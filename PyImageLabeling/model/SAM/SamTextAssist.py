from PyImageLabeling.model.Core import Core


# DINO floor: everything >= this is cached at Generate time; the dialog
# slider only refilters afterwards (instant, stable zones).
TEXT_DINO_FLOOR = 0.01
# Boxes SAM-refined eagerly at Generate (DINO-first order) + max extra
# boxes refined per slider move (lazy). Missing houses usually rank #7+;
# a hard cap silently drops them beyond any threshold, so lowering the
# slider refines more on demand instead.
TEXT_EAGER_BOXES = 12
TEXT_LAZY_PER_STEP = 12
TEXT_POOL_CAP = 40
TEXT_MAX_BOXES = TEXT_EAGER_BOXES  # legacy alias
# A "thing" (house, dog, …) covering more than this of the image is a
# detection failure (whole-image mask). Stuff queries are exempt.
TEXT_MAX_COVERAGE = 0.8


class SamTextAssist(Core):
    def __init__(self):
        super().__init__()
        self.sam_text_boxes = []
        self.sam_text_masks = []
        self.sam_text_refined = []
        self.sam_text_heat = None
        self.sam_text_colorheat = None
        self.sam_text_query = ""
        self.sam_text_source = ""
        self.sam_text_gen_threshold = 0.0

    def sam_text_generate(self, text, threshold):
        """Dialog flow, step 1: detect + refine once, cache everything.

        DINO runs at a fixed low floor (CLIPSeg fallback if empty), the
        top boxes are SAM-refined, then the current threshold selects
        the visible subset. Slider moves afterwards never recompute.
        Returns (ok, message).
        """
        import numpy as np
        from PyImageLabeling.model.SAM import textmask

        if bool(getattr(self, "_sam_batch_mode", False)):
            return (False, "Batch propagation running — wait for it "
                           "to finish…")
        self.sam_text_boxes = []
        self.sam_text_masks = []
        self.sam_text_query = text

        parsed = textmask.parse_query(text)
        phrase = parsed["phrase_en"]
        if not phrase:
            return (False, "Empty description. Example: "
                           "'chien rouge à gauche' / 'red dog on the left'.")
        image_item = self.get_current_image_item()
        label_item = self.get_current_label_item()
        if image_item is None or label_item is None:
            return (False, "Select an image and a label first.")

        ok, msg = self._ensure_sam_loaded()
        if not ok:
            return (False, msg)

        rgb = image_item.get_image_numpy_pixels_rgb()
        h, w = rgb.shape[:2]
        device = self._sam_params()["device"]

        # ── boxes with scores: DINO floor (+ CLIPSeg union if unsure) ──
        # DINO is precise spatially, CLIPSeg catches what DINO misses
        # (recall); verification layers below remove the junk.
        # CLIPSeg is skipped when DINO is already confident (speed).
        import time as _t0mod
        t_gen = _t0mod.time()
        boxes = []
        try:
            from PyImageLabeling.model.SAM import grounding
            expanded = grounding.expand_synonyms(text)
            boxes = grounding.text_to_boxes(
                rgb, expanded, device=device,
                box_threshold=TEXT_DINO_FLOOR)
            self.sam_text_source = "dino"
        except Exception as e:
            import traceback
            traceback.print_exc()
            return (False, f"Grounding backend failed:\n{e}")

        heat = None
        mean_dino = (sum(b["score"] for b in boxes) / len(boxes)
                     if boxes else 0.0)
        if len(boxes) < 3 or mean_dino < 0.35:
            try:
                heat, info = textmask.combined_heatmap(
                    rgb, parsed, device=device)
                prompts, _peak = textmask.heat_to_prompts(heat, 0.10)
                for pr in prompts[:TEXT_MAX_BOXES]:
                    cand = {"box": pr["box"], "score": pr["peak"]}
                    if not any(self._boxes_iou(cand["box"], b["box"]) > 0.7
                               for b in boxes):
                        boxes.append(cand)
                if not boxes and info["clip_peak"] < 0.15:
                    return (False,
                            f"Nothing found for '{text}' "
                            f"(peak {info['clip_peak']:.2f}).\n"
                            f"Try English nouns (e.g. 'dog').")
            except Exception as e:
                print(f"[text] CLIPSeg union failed: {e}")

        if not boxes:
            return (False,
                    f"Nothing found for '{text}'.\n"
                    f"Try English nouns (e.g. 'dog').")
        # Complete pool (never filtered, only marked): box order = score
        # order from DINO, CLIPSeg extras appended. Refining is lazy —
        # slider moves fill admitted-but-unrefined boxes on demand.
        boxes = boxes[:TEXT_POOL_CAP]
        self.sam_text_boxes = boxes
        self.sam_text_masks = [None] * len(boxes)
        self.sam_text_refined = [False] * len(boxes)
        self.sam_text_heat = heat
        self.sam_text_colorheat = None

        # ── SAM-refine top boxes eagerly (pos + neg points, cascade) ──
        self._sam_reset_for_image(image_item)
        path = image_item.path_image
        order = sorted(range(len(boxes)),
                       key=lambda i: -float(boxes[i].get("score", 0)))
        self._sam_text_refine_indices(
            rgb, path, order[:TEXT_EAGER_BOXES], heat, h, w)
        refined = sum(1 for m in self.sam_text_masks if m is not None)
        if refined == 0:
            if getattr(self, "_sam_last_error", None) == "gpu-oom":
                self._sam_consume_oom()
                return (False, "Out of memory. Caches purged — retry.")
            return (False, "SAM refinement failed. Try SAM Assist instead.")
        # drop whole-image zones for countable objects ("houses" must
        # never return 99% of the image; "flood water" may)
        n_giant = self._sam_mark_giant(
            h, w, text)
        if not any(m is not None for m in self.sam_text_masks):
            return (False,
                    "Only whole-image regions matched — try a more "
                    "specific description (color, position, …).")
        # color consistency: stated colors must actually be present
        self._sam_drop_offcolor(rgb)
        if not any(m is not None for m in self.sam_text_masks):
            return (False,
                    f"No '{' '.join(parsed.get('colors', []))}' found "
                    f"in the candidates — check the color.")
        # CLIP verification: mild rerank only (absolute CLIP values
        # overlap between right and wrong matches — never fail here).
        # Low best score only triggers a "low confidence" warning below.
        from PyImageLabeling.model.SAM import textmask as _tmv
        no_color = not bool(_tmv.expected_colors(parsed))
        _, clip_best = self._sam_clip_verify(rgb, text, device)
        warn = ""
        if no_color and clip_best < 0.26:
            warn = " (low confidence — please verify)"
        self.sam_text_gen_threshold = threshold
        ok, msg = self.sam_text_apply_threshold(threshold)
        if ok:
            import time as _t1mod
            msg = f"{msg} (took {_t1mod.time() - t_gen:.1f}s)"
        if ok and warn:
            msg = msg + warn
        return ok, msg

    def _sam_text_refine_indices(self, rgb, path, idx_list, heat, h, w):
        """Refine pool indices in place (pos + neg points, then cascade).

        Writes the best mask or None per index and marks them refined
        (dropped candidates are never retried). Returns newly refined count.
        """
        import numpy as np
        n = 0
        for i in idx_list:
            if self.sam_text_refined[i]:
                continue
            self.sam_text_refined[i] = True
            box = self.sam_text_boxes[i].get("box")
            if box is None:
                continue
            cx = (box[0] + box[2]) // 2
            cy = (box[1] + box[3]) // 2
            pts, lbs = self._sam_text_negatives(
                heat, box, cx, cy, h, w)
            masks, scores = self._sam_infer_candidates(
                rgb, path, pts, lbs, box)
            if masks is None:
                continue
            best = int(np.argmax(scores)) if len(scores) > 1 else 0
            mask = masks[best]
            # cascade: tight bbox around the mask, decode once more
            mask = self._sam_cascade_refine(rgb, path, mask)
            self.sam_text_masks[i] = mask
            n += 1
        return n

    def _sam_mark_giant(self, h, w, text):
        """Mark whole-image masks as dropped (None) for countable objects.

        "houses" must never return 99% of the image; "flood water" may.
        Giants survive only as sole confident candidate (close-up).
        Returns number marked.
        """
        from PyImageLabeling.model.SAM import textmask
        if textmask.is_stuff_query(text):
            return 0
        limit = TEXT_MAX_COVERAGE * h * w
        giants = [(i, float(self.sam_text_boxes[i].get("score", 0)))
                  for i, m in enumerate(self.sam_text_masks)
                  if m is not None and m.sum() > limit]
        if not giants:
            return 0
        small_ok = any(
            m is not None and m.sum() <= limit
            for m in self.sam_text_masks)
        if small_ok:
            for i, _ in giants:
                self.sam_text_masks[i] = None
            return len(giants)
        # only giants: keep the best confident one (close-up), else drop all
        giants.sort(key=lambda t: -t[0])
        if giants[0][0] >= 0.4:
            for i, _ in giants[1:]:
                self.sam_text_masks[i] = None
            return len(giants) - 1
        for i, _ in giants:
            self.sam_text_masks[i] = None
        return len(giants)

    @staticmethod
    def _sam_text_negatives(heat, box, cx, cy, h, w):
        """Positive center + one negative point.

        Negative = coldest heat pixel outside the dilated box (stops SAM
        bleeding); falls back to the farthest image corner (no heat).
        Returns (points, labels).
        """
        import numpy as np
        x1, y1, x2, y2 = box
        if heat is not None:
            dx = max(2, int((x2 - x1) * 0.15))
            dy = max(2, int((y2 - y1) * 0.15))
            work = heat.copy()
            work[max(0, y1 - dy):min(h, y2 + dy),
                 max(0, x1 - dx):min(w, x2 + dx)] = 2.0
            ny, nx = divmod(int(work.argmin()), w)
            return [[cx, cy], [int(nx), int(ny)]], [1, 0]
        corners = [(5, 5), (w - 6, 5), (5, h - 6), (w - 6, h - 6)]
        nx, ny = max(corners,
                     key=lambda p: (p[0] - cx) ** 2 + (p[1] - cy) ** 2)
        return [[cx, cy], [nx, ny]], [1, 0]

    def _sam_cascade_refine(self, rgb, path, mask):
        """One cascade round: tight bbox around mask -> decode again.

        Tightens loose masks; returns the refined mask (or the input if
        the second pass fails or is empty).
        """
        import numpy as np
        ys, xs = np.where(mask)
        if len(ys) == 0:
            return mask
        h, w = mask.shape[:2]
        pad = 0.03
        dx = max(2, int((xs.max() - xs.min()) * pad))
        dy = max(2, int((ys.max() - ys.min()) * pad))
        box = [max(0, int(xs.min() - dx)), max(0, int(ys.min() - dy)),
               min(w - 1, int(xs.max() + dx)),
               min(h - 1, int(ys.max() + dy))]
        cx, cy = (box[0] + box[2]) // 2, (box[1] + box[3]) // 2
        try:
            masks, scores = self._sam_infer_candidates(
                rgb, path, [[cx, cy]], [1], box)
        except Exception:
            return mask
        if masks is None:
            return mask
        best = int(np.argmax(scores)) if len(scores) > 1 else 0
        return masks[best]

    @staticmethod
    def _boxes_iou(box1, box2):
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])
        inter = max(0, x2 - x1) * max(0, y2 - y1)
        a1 = max(0, box1[2] - box1[0]) * max(0, box1[3] - box1[1])
        a2 = max(0, box2[2] - box2[0]) * max(0, box2[3] - box2[1])
        union = a1 + a2 - inter
        return inter / union if union > 0 else 0.0

    def _sam_zone_check_new(self, idx_list, h, w, colorheat):
        """Per-zone giant + color checks for lazily refined masks.

        Same rules as generate-time, but stable: never drops a previously
        visible zone (only the newcomers are judged).
        """
        from PyImageLabeling.model.SAM import textmask
        text = getattr(self, "sam_text_query", "")
        stuff = textmask.is_stuff_query(text)
        limit = TEXT_MAX_COVERAGE * h * w
        small_exists = any(
            mm is not None and mm.sum() <= limit
            for mm in self.sam_text_masks)
        for i in idx_list:
            m = self.sam_text_masks[i]
            if m is None:
                continue
            if not stuff and m.sum() > limit:
                if (small_exists or float(
                        self.sam_text_boxes[i].get("score", 0)) < 0.4):
                    self.sam_text_masks[i] = None
                    continue
            if (colorheat is not None
                    and float(colorheat[m].mean()) < 0.30):
                self.sam_text_masks[i] = None

    def _sam_drop_offcolor(self, rgb):
        """Drop refined masks lacking the expected colors (mean < 0.3).

        Expected = user-stated colors + noun-implied colors
        ("grass" must be green even if unstated).
        """
        import numpy as np
        from PyImageLabeling.model.SAM import textmask
        parsed = textmask.parse_query(
            getattr(self, "sam_text_query", ""))
        colors = textmask.expected_colors(parsed)
        if not colors:
            self.sam_text_colorheat = None
            return 0
        cheat = textmask.color_heatmap(rgb, colors)
        self.sam_text_colorheat = cheat
        n = 0
        for i, m in enumerate(self.sam_text_masks):
            if m is not None and float(cheat[m].mean()) < 0.30:
                self.sam_text_masks[i] = None
                n += 1
        if n:
            print(f"[text] color check dropped {n} candidate(s)")
        return n

    def _sam_clip_verify(self, rgb, text, device, rel_margin=0.08):
        """Mild rerank: drop candidates far below the best (CLIP).

        Only a relative margin — absolute CLIP values overlap between
        real and wrong matches, so this never fails everything.
        Returns (n_dropped, best_score).
        """
        import numpy as np
        try:
            from PyImageLabeling.model.SAM import relational
        except Exception:
            return 0
        idx = [i for i, m in enumerate(self.sam_text_masks)
               if m is not None]
        if not idx:
            return 0, 0.0
        try:
            scores = relational.score_candidates(
                rgb, [self.sam_text_masks[i] for i in idx],
                text, device=device)
        except Exception as e:
            print(f"[text] CLIP verify failed: {e}")
            return 0, 0.0
        print(f"[text] CLIP verify: {[round(s, 3) for s in scores]}")
        best = max(scores)
        keep = {i for i, s in zip(idx, scores) if s >= best - rel_margin}
        n = 0
        for i in idx:
            if i not in keep:
                self.sam_text_masks[i] = None
                n += 1
        if n:
            print(f"[text] CLIP verify dropped {n} candidate(s)")
        return n, best

    def sam_text_apply_threshold(self, threshold):
        """Dialog flow, step 2: refilter cached boxes + lazy-refine.

        Boxes admitted by the threshold but never refined are SAM-refined
        on demand (capped per call), so lowering the slider truly reveals
        more zones. The overlay always shows exactly what OK will paint.
        Returns (ok, message).
        """
        import numpy as np
        boxes = getattr(self, "sam_text_boxes", None) or []
        masks = getattr(self, "sam_text_masks", None) or []
        refined = getattr(self, "sam_text_refined", None) or []
        image_item = self.get_current_image_item()
        if not boxes or image_item is None:
            return (False, "Generate first: type a description.")
        # lazy: refine admitted-but-unrefined boxes (score order, capped)
        order = sorted(range(len(boxes)),
                       key=lambda i: -float(boxes[i].get("score", 0)))
        todo = [i for i in order
                if float(boxes[i].get("score", 0)) >= threshold
                and i < len(masks) and masks[i] is None
                and i < len(refined) and not refined[i]][:TEXT_LAZY_PER_STEP]
        if todo:
            rgb = image_item.get_image_numpy_pixels_rgb()
            h, w = rgb.shape[:2]
            path = image_item.path_image
            self._sam_text_refine_indices(
                rgb, path, todo,
                getattr(self, "sam_text_heat", None), h, w)
            masks = self.sam_text_masks
            self._sam_zone_check_new(
                todo, h, w,
                getattr(self, "sam_text_colorheat", None))
            masks = self.sam_text_masks
        visible = [m for b, m in zip(boxes, masks)
                   if m is not None and float(b.get("score", 0)) >= threshold]
        if not visible:
            self._sam_clear_preview_items()
            self.sam_preview_mask = None
            self.sam_preview_candidates = None
            self.sam_candidate_idx = 0
            hint = ""
            if threshold <= 0.02:
                hint = " (already widest search: rephrase the query)"
            return (False,
                    f"No zones pass {threshold:.2f} — lower the "
                    f"threshold.{hint}")
        stacked = np.stack(visible)
        self.sam_preview_candidates = stacked
        self.sam_candidate_scores = [1.0] * len(stacked)
        self.sam_candidate_idx = 0
        fused = np.logical_or.reduce(stacked)
        self._sam_show_preview(image_item, fused)
        n = len(visible)
        return (True,
                f"{n} zone(s) ≥ {threshold:.2f} — "
                f"Apply paints exactly this.")

    def sam_text_cycle(self, step=1):
        """Cycle within the visible subset. Returns (ok, message)."""
        cands = getattr(self, "sam_preview_candidates", None)
        if cands is None or len(cands) <= 1:
            return (False, "Single zone — nothing to cycle.")
        self.sam_candidate_idx = (
            (self.sam_candidate_idx + step) % len(cands))
        image_item = self.get_current_image_item()
        if image_item is None:
            return (False, "")
        self._sam_show_preview(image_item, cands[self.sam_candidate_idx])
        i = self.sam_candidate_idx + 1
        return (True, f"Zone {i}/{len(cands)} — Apply paints this one.")

    def sam_text_preview(self, text, threshold=0.5):
        """Text-to-mask: description -> SAM-refined preview.

        Returns (ok, message). On success the fused mask is shown as a
        preview (same Apply/Cancel flow as SAM Assist and ML).
        """
        import numpy as np
        from PyImageLabeling.model.SAM import textmask

        if bool(getattr(self, "_sam_batch_mode", False)):
            return (False, "Batch propagation running — wait for it "
                           "to finish…")
        parsed = textmask.parse_query(text)
        phrase = parsed["phrase_en"]
        if not phrase:
            return (False, "Empty description. Example: "
                           "'chien rouge à gauche' / 'red dog on the left'.")
        image_item = self.get_current_image_item()
        label_item = self.get_current_label_item()
        if image_item is None or label_item is None:
            return (False, "Select an image and a label first.")

        ok, msg = self._ensure_sam_loaded()
        if not ok:
            return (False, msg)

        rgb = image_item.get_image_numpy_pixels_rgb()
        h, w = rgb.shape[:2]
        device = self._sam_params()["device"]

        # ── Universal strategy: SAM auto + CLIP scoring ──
        # Works for ANY image type (drone, medical, white bg, etc.)
        # because SAM segments everything without knowing the object.
        try:
            from PyImageLabeling.model.SAM import sam2_auto, relational
            auto_masks = sam2_auto.generate_masks(rgb, device=device)
            if auto_masks is not None and len(auto_masks) > 0:
                best_mask, best_score, all_scores = (
                    relational.pick_best_candidate(
                        rgb, auto_masks, text, device=device))
                if best_mask is not None:
                    fused = best_mask
                    n_ok = 1
                    self.sam_preview_candidates = auto_masks
                    self.sam_candidate_scores = all_scores
                    self.sam_candidate_idx = int(np.argmax(all_scores))
                    self._sam_show_preview(image_item, fused)
                    return (True,
                            f"'{text}': auto-masked "
                            f"(CLIP score {best_score:.2f}, "
                            f"{len(auto_masks)} candidates) — "
                            f"Apply to validate.")
        except Exception as e:
            print(f"[auto-mask] failed: {e}")

        # ── Grounding-DINO: text → boxes (spatial understanding) ──
        try:
            from PyImageLabeling.model.SAM import grounding
            expanded = grounding.expand_synonyms(text)
            dino_boxes = grounding.text_to_boxes(
                rgb, expanded, device=device, box_threshold=threshold)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return (False, f"Grounding backend failed:\n{e}")

        if not dino_boxes:
            # fallback: CLIPSeg heatmap
            try:
                heat, info = textmask.combined_heatmap(
                    rgb, parsed, device=device)
            except Exception as e:
                return (False, f"Text backend failed:\n{e}")
            if info["clip_peak"] < 0.15:
                return (False,
                        f"Nothing found for '{text}' "
                        f"(peak {info['clip_peak']:.2f}).\n"
                        f"Try English nouns (e.g. 'dog').")
            prompts, peak = textmask.heat_to_prompts(heat, threshold)
            if not prompts:
                return (False, f"Heat too diffuse (peak {peak:.2f}).")
            dino_boxes = [{"box": pr["box"], "score": pr["peak"]}
                          for pr in prompts[:4]]

        # ── SAM refinement: boxes → precise masks ──
        self._sam_reset_for_image(image_item)
        path = image_item.path_image
        refined = []  # (det, masks, scores)
        for det in dino_boxes[:TEXT_MAX_BOXES]:
            box = det["box"]
            if box is None:
                continue
            cx = (box[0] + box[2]) // 2
            cy = (box[1] + box[3]) // 2
            masks, scores = self._sam_infer_candidates(
                rgb, path, [[cx, cy]], [1], box)
            if masks is None:
                continue
            refined.append((det, masks, scores))

        if not refined:
            if getattr(self, "_sam_last_error", None) == "gpu-oom":
                self._sam_consume_oom()
                return (False, "Out of memory. Caches purged — retry.")
            return (False, "SAM refinement failed. Try other points "
                           "with SAM Assist instead.")

        # ── drop whole-image zones for countable objects ──
        # ("houses" must never return 99% of the image; "flood water" may)
        from PyImageLabeling.model.SAM import textmask as _tm
        if not _tm.is_stuff_query(text):
            limit = TEXT_MAX_COVERAGE * h * w
            kept = []
            for det, masks, scores in refined:
                best = int(np.argmax(scores)) if len(scores) > 1 else 0
                if masks[best].sum() <= limit:
                    kept.append((det, masks, scores))
            if not kept:
                return (False,
                        "Only whole-image regions matched — try a more "
                        "specific description (color, position, …).")
            refined = kept

        fused = np.zeros((h, w), dtype=bool)
        all_masks, kept_dets, n_ok = [], [], 0
        for det, masks, scores in refined:
            all_masks.append(masks)
            kept_dets.append(det)
            best = int(np.argmax(scores)) if len(scores) > 1 else 0
            fused |= masks[best]
            n_ok += 1

        # ── Relational scoring for multi-instance disambiguation ──
        relational_words = {"background", "foreground", "behind", "front",
                            "left", "right", "top", "bottom", "center",
                            "bigger", "smaller", "closest", "farthest",
                            "nearest", "furthest", "first", "last"}
        has_relational = any(w in text.lower().split()
                             for w in relational_words)
        if has_relational and len(all_masks) > 0:
            try:
                from PyImageLabeling.model.SAM import relational
                flat_masks = []
                for masks in all_masks:
                    for m in masks:
                        if m.sum() > 0:
                            flat_masks.append(m)
                if len(flat_masks) > 1:
                    best_mask, best_score, all_scores = (
                        relational.pick_best_candidate(
                            rgb, flat_masks, text, device=device))
                    if best_mask is not None:
                        fused = best_mask
                        n_ok = 1
            except Exception as e:
                print(f"[relational] scoring failed: {e}")

        # store kept candidates for cycling
        self.sam_preview_candidates = np.stack(
            [m[0] for m in all_masks]) if all_masks else fused[None]
        self.sam_candidate_scores = [float(d["score"]) for d in kept_dets]
        self.sam_candidate_idx = 0
        self._sam_show_preview(image_item, fused)
        top = (kept_dets[0]["score"] if kept_dets else 0.0)
        return (True,
                f"'{text}': {n_ok} object(s) found "
                f"(threshold {threshold:.2f}), "
                f"best box score {top:.2f} — "
                f"Apply to validate.")
