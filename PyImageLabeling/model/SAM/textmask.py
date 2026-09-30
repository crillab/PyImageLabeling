"""French/English query parsing + CLIPSeg text-to-mask + SAM refinement.

100% local: rule-based FR/EN parser, CLIPSeg heatmap, SAM precision.
Supports colors, shapes (via CLIP English), and coarse localization
(left/right/top/bottom/center/corners, FR + EN).

NOTE: on case-insensitive filesystems this module must keep a unique
lowercase name (do NOT add a TextMask.py sibling).
"""

import numpy as np

CLIPSEG_MODEL_ID = "CIDAS/clipseg-rd64-refined"

# ----------------------------------------------------------------------
# Dictionaries (French -> English, all lowercase)
# ----------------------------------------------------------------------
COLORS_FR_EN = {
    "rouge": "red", "bleu": "blue", "bleue": "blue", "bleus": "blue",
    "vert": "green", "verte": "green", "verts": "green",
    "jaune": "yellow", "orange": "orange", "rose": "pink",
    "violet": "purple", "violette": "purple", "marron": "brown",
    "noir": "black", "noire": "black", "blanc": "white", "blanche": "white",
    "gris": "gray", "grise": "gray", "cyan": "cyan",
    "turquoise": "turquoise", "beige": "beige", "doré": "golden",
    "dore": "golden", "argenté": "silver", "argente": "silver",
}

SIZES_FR_EN = {
    "grand": "big", "grande": "big", "grands": "big", "gros": "big",
    "grosse": "big", "petit": "small", "petite": "small", "petits": "small",
}

SHAPES_FR_EN = {
    "cercle": "circle", "cercles": "circles", "rond": "circle",
    "carré": "square", "carre": "square", "carrés": "squares",
    "rectangle": "rectangle", "triangle": "triangle", "ovale": "oval",
    "ellipse": "ellipse", "losange": "diamond", "croix": "cross",
    "étoile": "star", "etoile": "star", "flèche": "arrow", "fleche": "arrow",
    "ligne": "line", "lignes": "lines", "point": "dot", "tache": "spot",
    "bande": "stripe", "anneau": "ring",
}

# Common nouns French -> English (open vocabulary falls back to raw text)
NOUNS_FR_EN = {
    "chien": "dog", "chiens": "dogs", "chat": "cat", "chats": "cats",
    "oiseau": "bird", "oiseaux": "birds", "cheval": "horse",
    "vache": "cow", "mouton": "sheep", "cochon": "pig", "lapin": "rabbit",
    "souris": "mouse", "poisson": "fish",
    "voiture": "car", "voitures": "cars", "camion": "truck", "bus": "bus",
    "train": "train", "avion": "plane", "bateau": "boat", "vélo": "bike",
    "velo": "bike", "moto": "motorcycle",
    "personne": "person", "personnes": "people", "homme": "man",
    "femme": "woman", "enfant": "child", "enfants": "children",
    "visage": "face", "main": "hand", "mains": "hands", "oeil": "eye",
    "yeux": "eyes",
    "arbre": "tree", "arbres": "trees", "fleur": "flower",
    "feuille": "leaf", "herbe": "grass", "ciel": "sky", "nuage": "cloud",
    "soleil": "sun", "lune": "moon", "montagne": "mountain", "eau": "water",
    "mer": "sea", "rivière": "river", "riviere": "river", "route": "road",
    "maison": "house", "bâtiment": "building", "batiment": "building",
    "porte": "door", "fenêtre": "window", "fenetre": "window",
    "toit": "roof", "mur": "wall", "chaise": "chair", "table": "table",
    "lit": "bed", "bouteille": "bottle", "verre": "glass",
    "tasse": "cup", "livre": "book", "téléphone": "phone",
    "telephone": "phone", "ordinateur": "computer", "écran": "screen",
    "ecran": "screen", "ballon": "ball", "parapluie": "umbrella",
    "sac": "bag", "chapeau": "hat", "chaussure": "shoe",
    # medical bonus
    "tumeur": "tumor", "cellule": "cell", "poumon": "lung",
    "coeur": "heart", "cerveau": "brain", "os": "bone", "peau": "skin",
    "organe": "organ", "vaisseau": "vessel", "lésion": "lesion",
    "lesion": "lesion", "nodule": "nodule", "kyste": "cyst",
}

# Spatial keywords -> region id. Multi-word first (longest match wins).
REGIONS = [
    (["en haut à gauche", "en haut a gauche", "upper left", "top left"],
     "top-left"),
    (["en haut à droite", "en haut a droite", "upper right", "top right"],
     "top-right"),
    (["en bas à gauche", "en bas a gauche", "lower left", "bottom left"],
     "bottom-left"),
    (["en bas à droite", "en bas a droite", "lower right", "bottom right"],
     "bottom-right"),
    (["à gauche", "a gauche", "on the left", "left side", "on left"], "left"),
    (["à droite", "a droite", "on the right", "right side", "on right"],
     "right"),
    (["en haut", "au-dessus", "au dessus", "on top", "at the top", "upper",
      "top"], "top"),
    (["en bas", "en dessous", "au-dessous", "au dessous", "at the bottom",
      "lower", "bottom"], "bottom"),
    (["au centre", "au milieu", "in the center", "in the middle", "center",
      "middle", "centre", "milieu"], "center"),
    (["gauche", "left"], "left"),
    (["droite", "droit", "right"], "right"),
    (["haut", "dessus"], "top"),
    (["bas", "dessous"], "bottom"),
]

FILLER_WORDS = {
    # French
    "le", "la", "les", "l", "un", "une", "des", "du", "de", "d", "au",
    "aux", "à", "a", "en", "dans", "sur", "sous", "avec", "sans", "qui",
    "que", "est", "sont", "ce", "cet", "cette", "ces", "mon", "ma", "mes",
    "son", "sa", "ses", "leur", "leurs", "je", "veux", "masque", "masquer",
    "trouve", "trouver", "voir", "montre", "montrer", "moi", "stp", "sil",
    "vous", "plait", "segmente", "segmenter", "isole", "isoler",
    # English
    "the", "a", "an", "of", "on", "in", "at", "with", "without", "that",
    "which", "is", "are", "this", "these", "those", "my", "your", "please",
    "mask", "segment", "find", "show", "me",
    # vague object words (no semantic value, drop them)
    "truc", "trucs", "machin", "machins", "chose", "choses", "objet",
    "objets", "thing", "things", "object", "objects", "stuff",
}


def _normalize(text):
    import unicodedata
    text = text.lower().strip()
    for ch in [",", ";", "!", "?", ".", ":", "'", "’", "'", "\"", "(", ")",
               "-"]:
        text = text.replace(ch, " ")
    folded = "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn")
    return text, folded


def _find_region(text, folded):
    for variants, region in REGIONS:
        for v in variants:
            import unicodedata
            vf = "".join(c for c in unicodedata.normalize("NFD", v)
                         if unicodedata.category(c) != "Mn")
            if vf in folded:
                return region, vf
    return None, None


def parse_query(text):
    """Parse a FR/EN description.

    Returns dict(phrase_en, region, colors, debug).
    Example: "le chien rouge à gauche" ->
             {"phrase_en": "red dog", "region": "left", ...}
    """
    raw, folded = _normalize(text)
    region, matched = _find_region(raw, folded)
    work = folded
    if matched:
        work = work.replace(matched, " ", 1)

    tokens = [t for t in work.split() if t]
    colors, sizes, shapes, nouns = [], [], [], []
    for tok in tokens:
        if tok in FILLER_WORDS:
            continue
        if tok in COLORS_FR_EN:
            colors.append(COLORS_FR_EN[tok])
        elif tok in SIZES_FR_EN:
            sizes.append(SIZES_FR_EN[tok])
        elif tok in SHAPES_FR_EN:
            shapes.append(SHAPES_FR_EN[tok])
        elif tok in NOUNS_FR_EN:
            nouns.append(NOUNS_FR_EN[tok])
        else:
            nouns.append(tok)  # already English / proper noun

    parts = sizes + colors + shapes + nouns
    phrase_en = " ".join(parts).strip()
    if not phrase_en and colors:
        # "le rouge à gauche" -> CLIP gets "red", pixel signal does the rest
        phrase_en = " ".join(colors)
    return {"phrase_en": phrase_en, "region": region, "colors": colors,
            "nouns": nouns, "shapes": shapes,
            "has_semantic": bool(nouns or shapes),
            "debug": f"tokens={tokens}"}


# Nouns with an expected color (used for the color-consistency check
# even when the user didn't state a color: "grass" must be green).
NOUN_COLORS = {
    "grass": ["green"], "water": ["blue"], "sky": ["blue"],
    "sea": ["blue"], "ocean": ["blue"], "river": ["blue"],
    "lake": ["blue"], "snow": ["white"], "sand": ["beige"],
    "road": ["gray"], "rock": ["gray"], "tree": ["green"],
    "forest": ["green"], "leaf": ["green"], "leaves": ["green"],
    "blood": ["red"],
}


def expected_colors(parsed):
    """Explicit colors + noun-implied colors."""
    colors = list(parsed.get("colors", []))
    for n in parsed.get("nouns", []):
        for c in NOUN_COLORS.get(n, []):
            if c not in colors:
                colors.append(c)
    return colors


def region_mask(h, w, region):
    """Binary HxW mask for a coarse region (None = whole image)."""
    m = np.zeros((h, w), dtype=bool)
    if region is None:
        m[:] = True
        return m
    mx, my = w // 2, h // 2
    if region in ("left", "top-left", "bottom-left"):
        m[:, :mx] = True
    if region in ("right", "top-right", "bottom-right"):
        m[:, mx:] = True
    if region in ("top", "top-left", "top-right"):
        m[:my, :] = True
    if region in ("bottom", "bottom-left", "bottom-right"):
        m[my:, :] = True
    if region == "center":
        m[my // 2:my + my // 2, mx // 2:mx + mx // 2] = True
    if not m.any():
        m[:] = True
    return m


# ----------------------------------------------------------------------
# Explicit color signal (HSV pixel space).
#
# The user-stated color dominates the fusion: CLIP adjectives are soft,
# this measurement is deterministic. OpenCV HSV: H in [0,179].
# ----------------------------------------------------------------------
COLOR_HSV = {
    # name: (hue_center or None, hue_half_width, s_min, s_max, v_min, v_max)
    "red":      (0,   10, 70,  255, 50,  255),
    "orange":   (12,  8,  90,  255, 80,  255),
    "yellow":   (28,  10, 80,  255, 80,  255),
    "green":    (70,  20, 60,  255, 50,  255),
    "cyan":     (90,  8,  80,  255, 80,  255),
    "turquoise": (85, 12, 80,  255, 80,  255),
    "blue":     (110, 15, 70,  255, 50,  255),
    "purple":   (140, 12, 70,  255, 50,  255),
    "pink":     (150, 12, 70,  255, 120, 255),
    "brown":    (12,  10, 50,  200, 40,  180),
    "beige":    (20,  10, 25,  130, 150, 255),
    "golden":   (22,  8,  120, 255, 150, 255),
    "black":    (None, 0, 0,   255, 0,   60),
    "white":    (None, 0, 0,   50,  180, 255),
    "gray":     (None, 0, 0,   60,  60,  180),
    "grey":     (None, 0, 0,   60,  60,  180),
    "silver":   (None, 0, 0,   50,  150, 255),
}


def color_heatmap(rgb, colors_en):
    """Per-pixel color similarity in [0,1] (max over requested colors).

    Empty colors_en -> all-ones (neutral element of the fusion).
    """
    h, w = rgb.shape[:2]
    if not colors_en:
        return np.ones((h, w), dtype=np.float32)
    import cv2
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV).astype(np.float32)
    H, S, V = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
    best = np.zeros((h, w), dtype=np.float32)
    for name in colors_en:
        spec = COLOR_HSV.get(name)
        if spec is None:
            continue
        hc, hw, s_min, s_max, v_min, v_max = spec
        gate = ((S >= s_min) & (S <= s_max)
                & (V >= v_min) & (V <= v_max)).astype(np.float32)
        if hc is None:
            score = gate  # achromatic: gates only
        else:
            dh = np.abs(H - hc)
            dh = np.minimum(dh, 180.0 - dh)
            hue_score = np.clip(1.0 - dh / max(hw, 1e-6), 0, 1)
            score = hue_score * gate
        best = np.maximum(best, score)
    return best


def combined_heatmap(rgb, parsed, device="cuda", region_outside=0.35):
    """Balanced fusion of the three cues: semantics, color, location.

    No cue gets veto power:
    - semantics (CLIP) always applies (base signal),
    - color modulates softly (x0.5 min / x1.0 max) when a noun or shape
      is present; it leads only for color-only queries ("le rouge"),
    - region is a soft preference (x0.5 outside), never a hard cut.

    Returns (heat, info) with info = {clip_peak, color_peak, phrase}.
    """
    heat_clip = np.clip(text_heatmap(rgb, parsed["phrase_en"],
                                     device=device), 0, 1)
    clip_peak = float(heat_clip.max())
    colors = parsed.get("colors", [])
    if colors:
        heat_color = color_heatmap(rgb, colors)
        color_peak = float(heat_color.max())
        if parsed.get("has_semantic"):
            # specific query: semantics must agree, color weights the vote
            heat = heat_clip * (0.5 + 0.5 * np.clip(heat_color, 0, 1))
        else:
            # vague query ("le truc rouge"): color leads, semantics backs
            heat = (np.power(np.clip(heat_color, 0, 1), 0.7)
                    * np.power(heat_clip, 0.3))
    else:
        color_peak = 1.0
        heat = heat_clip
    region = parsed.get("region")
    if region is not None:
        rm = region_mask(*heat.shape, region).astype(np.float32)
        heat = heat * np.where(rm, 1.0, region_outside)
    return heat.astype(np.float32), {"clip_peak": clip_peak,
                                     "color_peak": color_peak,
                                     "phrase": parsed["phrase_en"]}


# ----------------------------------------------------------------------
# Stuff (uncountable scene regions) vs things (countable objects).
# Stuff may legitimately cover most of the image ("flood water");
# a "thing" ("house", "dog") covering >80% is a detection failure.
# ----------------------------------------------------------------------
STUFF_WORDS = {
    "water", "flood", "sea", "ocean", "river", "lake", "pond", "stream",
    "sky", "cloud", "grass", "field", "ground", "road", "sand", "snow",
    "forest", "beach", "mountain", "hill", "background", "foreground",
    "desert", "ice",
}


def _region_words():
    import unicodedata
    words = set()
    for variants, _region in REGIONS:
        for v in variants:
            vf = "".join(c for c in unicodedata.normalize("NFD", v)
                         if unicodedata.category(c) != "Mn")
            words.update(vf.split())
    return words


_REGION_WORDS = _region_words()


def is_stuff_query(text):
    """True only if the description is about scene matter, not an object.

    Colors/sizes/positions are modifiers and don't count. Any noun, shape
    or unknown word that isn't stuff itself makes it a thing query
    ("houses in the water" -> thing; "flood water" -> stuff).
    """
    try:
        _raw, folded = _normalize(text)
        toks = [t for t in folded.split()
                if t not in FILLER_WORDS and t not in _REGION_WORDS]
        saw_stuff = False
        for t in toks:
            if t in COLORS_FR_EN or t in SIZES_FR_EN:
                continue
            en = SHAPES_FR_EN.get(t, NOUNS_FR_EN.get(t))
            if en is None and t not in STUFF_WORDS:
                return False  # unknown word = probably an object noun
            if (en or t) in STUFF_WORDS or t in STUFF_WORDS:
                saw_stuff = True
                continue
            return False
        return saw_stuff
    except Exception:
        return False


_clip_processor = None
_clip_model = None
_clip_device = None


def ensure_clipseg(device="cuda"):
    global _clip_processor, _clip_model, _clip_device
    if _clip_model is not None:
        return _clip_processor, _clip_model, _clip_device
    import torch
    from transformers import (CLIPSegForImageSegmentation, CLIPSegProcessor)
    dev = device
    if dev == "auto" or dev is None:
        dev = "cuda" if torch.cuda.is_available() else "cpu"
    if dev == "cuda" and not torch.cuda.is_available():
        dev = "cpu"
    _clip_processor = CLIPSegProcessor.from_pretrained(CLIPSEG_MODEL_ID)
    _clip_model = CLIPSegForImageSegmentation.from_pretrained(
        CLIPSEG_MODEL_ID).to(dev).eval()
    _clip_device = dev
    print(f"[textmask] CLIPSeg on {dev}")
    return _clip_processor, _clip_model, _clip_device


def text_heatmap(rgb, phrase_en, device="cuda"):
    """CLIPSeg probability heatmap HxW for an English phrase."""
    import torch
    import torch.nn.functional as F
    from PIL import Image
    h, w = rgb.shape[:2]
    processor, model, dev = ensure_clipseg(device)
    inputs = processor(text=[phrase_en], images=[Image.fromarray(rgb)],
                       return_tensors="pt", padding=True)
    inputs = {k: (v.to(dev) if hasattr(v, "to") else v)
              for k, v in inputs.items()}
    from PyImageLabeling.model.SAM.precision import cuda_autocast
    with torch.no_grad(), cuda_autocast(dev):
        out = model(**inputs)
    heat = F.interpolate(out.logits[None].float(), size=(h, w),
                         mode="bilinear", align_corners=False)[0, 0]
    return heat.sigmoid().cpu().numpy()


def heat_to_prompts(heat, threshold=0.5, min_area_ratio=0.0002):
    """Connected components of the heatmap -> SAM prompts each.

    Returns (prompts, peak_global), prompts as list of
    dict(points, labels, box) in image pixels.
    """
    import cv2
    h, w = heat.shape
    binary = (heat >= threshold).astype(np.uint8)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(binary, 8)
    prompts = []
    peak_global = float(heat.max())
    for i in range(1, n):
        area = stats[i, cv2.CC_STAT_AREA]
        if area < max(4, min_area_ratio * h * w):
            continue
        comp = (lab == i)
        # positive point = hottest pixel inside component
        masked = np.where(comp, heat, -1)
        fy, fx = divmod(int(masked.argmax()), w)
        x = stats[i, cv2.CC_STAT_LEFT]
        y = stats[i, cv2.CC_STAT_TOP]
        hw = stats[i, cv2.CC_STAT_WIDTH]
        hh = stats[i, cv2.CC_STAT_HEIGHT]
        pad = 0.05
        dx, dy = hw * pad, hh * pad
        box = [max(0, int(x - dx)), max(0, int(y - dy)),
               min(w - 1, int(x + hw + dx)), min(h - 1, int(y + hh + dy))]
        # negative point = coldest pixel outside component
        cold = np.where(comp, 2.0, heat)
        ny, nx = divmod(int(cold.argmin()), w)
        prompts.append({"points": [[int(fx), int(fy)], [int(nx), int(ny)]],
                        "labels": [1, 0],
                        "box": box,
                        "peak": float(heat[comp].max()),
                        "area": int(area)})
    prompts.sort(key=lambda p: -p["peak"])
    return prompts, peak_global
