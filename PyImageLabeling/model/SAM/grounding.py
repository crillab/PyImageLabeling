"""Grounding-DINO backend: text → bounding boxes with spatial understanding.

Much stronger than CLIPSeg for:
- referring expressions ("dog of the background", "left", "behind")
- multi-instance disambiguation
- precise localization

Outputs boxes that SAM refines into pixel-perfect masks.
"""

import numpy as np

GROUNDING_MODEL_ID = "IDEA-Research/grounding-dino-tiny"

_grounding_model = None
_grounding_processor = None
_grounding_device = None


def ensure_grounding(device="cuda"):
    global _grounding_model, _grounding_processor, _grounding_device
    if _grounding_model is not None:
        return _grounding_model, _grounding_processor, _grounding_device
    import torch
    from transformers import AutoModelForZeroShotObjectDetection, AutoProcessor
    dev = device
    if dev == "auto" or dev is None:
        dev = "cuda" if torch.cuda.is_available() else "cpu"
    if dev == "cuda" and not torch.cuda.is_available():
        dev = "cpu"
    _grounding_processor = AutoProcessor.from_pretrained(GROUNDING_MODEL_ID)
    _grounding_model = AutoModelForZeroShotObjectDetection.from_pretrained(
        GROUNDING_MODEL_ID).to(dev).eval()
    _grounding_device = dev
    print(f"[grounding] DINO on {dev}")
    return _grounding_model, _grounding_processor, _grounding_device


def text_to_boxes(rgb, description, device="cuda", box_threshold=0.15,
                  text_threshold=0.1, scales=(1.0, 1.5)):
    """Grounding-DINO: description → list of (box, score).

    Returns list of dict(box=[x1,y1,x2,y2], score=float) in pixel coords,
    sorted by score descending. Empty list if nothing found.

    Multi-scale: DINO runs at 1.0x and 1.5x (small/far objects emerge at
    higher resolution); boxes are mapped back, merged and deduplicated.

    Note: box_threshold is applied client-side after a low-threshold DINO
    pass, so the zones stay stable and only the count changes with the
    user's threshold (DINO's internal NMS would otherwise reshuffle boxes).
    """
    import torch
    from PIL import Image
    h, w = rgb.shape[:2]
    model, processor, dev = ensure_grounding(device)
    text = description.lower().strip()
    if not text.endswith("."):
        text += "."
    all_boxes = []
    for scale in scales:
        if scale == 1.0:
            pil_img, sw, sh, inv = Image.fromarray(rgb), w, h, 1.0
        else:
            sw, sh = min(int(w * scale), 1600), min(int(h * scale), 1600)
            if sw <= w and sh <= h:
                continue
            inv = w / sw
            pil_img = Image.fromarray(rgb).resize(
                (sw, sh), Image.BILINEAR)
        inputs = processor(images=pil_img, text=text, return_tensors="pt")
        inputs = {k: (v.to(dev) if hasattr(v, "to") else v)
                  for k, v in inputs.items()}
        from PyImageLabeling.model.SAM.precision import cuda_autocast
        with torch.no_grad(), cuda_autocast(dev):
            outputs = model(**inputs)
        # always run DINO at a very low floor so NMS keeps stable zones;
        # the user's threshold is applied client-side afterwards
        results = processor.post_process_grounded_object_detection(
            outputs,
            inputs["input_ids"],
            threshold=0.01,
            text_threshold=0.01,
            target_sizes=[(sh, sw)],
        )[0]
        for box, score in zip(results["boxes"], results["scores"]):
            x1, y1, x2, y2 = [c * inv for c in box.tolist()]
            all_boxes.append({
                "box": [int(x1), int(y1), int(x2), int(y2)],
                "score": float(score),
            })
        del inputs, outputs
    # deduplicate across scales (IoU > 0.7: keep adjacent houses
    # separate), keep highest score
    merged = []
    for b in sorted(all_boxes, key=lambda x: -x["score"]):
        if any(_box_iou(b["box"], m["box"]) > 0.7 for m in merged):
            continue
        merged.append(b)
    boxes = [b for b in merged if b["score"] >= box_threshold]
    boxes.sort(key=lambda b: -b["score"])
    return boxes


def text_to_boxes_multi(rgb, description, device="cuda", box_threshold=0.15):
    """Multi-prompt DINO: try multiple text variations, merge results.

    Strategy:
    1. Run DINO once per variation at very low threshold (0.05)
    2. Collect all boxes
    3. Filter by user's threshold client-side (stable zones)
    4. Deduplicate by IoU

    Returns merged list of boxes, sorted by score descending.
    """
    from PIL import Image
    h, w = rgb.shape[:2]
    variations = _generate_variations(description)
    all_boxes = []
    for var in variations:
        try:
            # always run at very low threshold for stable NMS
            boxes = text_to_boxes(rgb, var, device=device,
                                  box_threshold=0.05)
            all_boxes.extend(boxes)
        except Exception:
            continue
    # filter by user's threshold client-side (zones stay stable)
    filtered = [b for b in all_boxes if b["score"] >= box_threshold]
    # deduplicate by IoU > 0.7 (keep adjacent objects separate),
    # keep highest score
    merged = []
    for b in sorted(filtered, key=lambda x: -x["score"]):
        is_dup = False
        for m in merged:
            if _box_iou(b["box"], m["box"]) > 0.7:
                is_dup = True
                break
        if not is_dup:
            merged.append(b)
    return merged


def _generate_variations(description):
    """Generate text variations for robust matching."""
    desc = description.lower().strip()
    variations = [desc]
    # synonym expansion
    expanded = expand_synonyms(desc)
    if expanded != desc:
        variations.append(expanded)
    # simplified: remove relational words
    relational = {"background", "foreground", "behind", "front",
                  "left", "right", "top", "bottom", "center",
                  "bigger", "smaller", "closest", "farthest",
                  "nearest", "furthest", "first", "last", "of", "the", "a"}
    words = [w for w in desc.split() if w not in relational]
    if len(words) >= 1 and " ".join(words) != desc:
        variations.append(" ".join(words))
    # with "a" prefix
    if not desc.startswith("a "):
        variations.append("a " + desc)
    return list(dict.fromkeys(variations))  # deduplicate, keep order


def _box_iou(box1, box2):
    """IoU between two boxes [x1, y1, x2, y2]."""
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
    area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
    union = area1 + area2 - inter
    return inter / union if union > 0 else 0.0


# Synonym expansion for universal coverage
SYNONYMS = {
    "water": ["water", "flood", "river", "lake", "ocean", "sea", "stream"],
    "mountain": ["mountain", "hill", "peak", "ridge", "cliff"],
    "tree": ["tree", "forest", "wood", "branch", "trunk"],
    "cell": ["cell", "cells", "nucleus", "tissue", "microscope"],
    "road": ["road", "street", "path", "highway", "lane"],
    "building": ["building", "house", "structure", "wall", "roof"],
    "car": ["car", "vehicle", "truck", "bus", "automobile"],
    "person": ["person", "people", "human", "man", "woman", "child"],
    "animal": ["animal", "creature", "wildlife", "beast"],
    "sky": ["sky", "cloud", "clouds", "atmosphere"],
    "grass": ["grass", "lawn", "meadow", "field", "vegetation"],
    "rock": ["rock", "rocks", "stone", "boulder", "cliff"],
    "sand": ["sand", "beach", "desert", "dune"],
    "snow": ["snow", "ice", "glacier", "frost"],
    "fire": ["fire", "flame", "smoke", "burning"],
    "dog": ["dog", "puppy", "canine", "pet"],
    "cat": ["cat", "kitten", "feline", "pet"],
    "bird": ["bird", "avian", "wing", "feather"],
    "fish": ["fish", "aquatic", "marine", "swimming"],
    "flower": ["flower", "blossom", "petal", "plant"],
    "leaf": ["leaf", "leaves", "foliage", "plant"],
    "bridge": ["bridge", "overpass", "viaduct", "span"],
    "river": ["river", "stream", "creek", "waterway", "water"],
    "ocean": ["ocean", "sea", "water", "wave", "coast"],
    "desert": ["desert", "sand", "dune", "arid", "dry"],
    "island": ["island", "land", "shore", "coast"],
    "valley": ["valley", "canyon", "gorge", "ravine", "hollow"],
    "cave": ["cave", "cavern", "tunnel", "underground"],
    "bridge": ["bridge", "overpass", "viaduct", "span"],
    "tower": ["tower", "spire", "minaret", "lighthouse"],
    "castle": ["castle", "fortress", "palace", "citadel"],
    "church": ["church", "cathedral", "chapel", "temple", "mosque"],
    "hospital": ["hospital", "clinic", "medical", "health"],
    "school": ["school", "university", "college", "education"],
    "stadium": ["stadium", "arena", "sports", "field"],
    "park": ["park", "garden", "green", "recreation"],
    "parking": ["parking", "lot", "garage", "cars"],
    "airport": ["airport", "runway", "terminal", "aviation"],
    "station": ["station", "depot", "terminal", "transport"],
    "harbor": ["harbor", "port", "marina", "dock", "boats"],
    "farm": ["farm", "field", "crop", "agriculture", "rural"],
    "factory": ["factory", "industrial", "plant", "manufacturing"],
    "office": ["office", "building", "commercial", "work"],
    "shop": ["shop", "store", "market", "retail", "commerce"],
    "restaurant": ["restaurant", "cafe", "dining", "food", "kitchen"],
    "hotel": ["hotel", "motel", "lodging", "resort", "accommodation"],
    "library": ["library", "books", "study", "reading"],
    "museum": ["museum", "gallery", "art", "exhibition"],
    "theater": ["theater", "cinema", "movie", "performance", "stage"],
    "gym": ["gym", "fitness", "exercise", "workout", "sports"],
    "pool": ["pool", "swimming", "water", "recreation"],
    "beach": ["beach", "shore", "coast", "sand", "ocean"],
    "forest": ["forest", "woods", "trees", "jungle", "wilderness"],
    "jungle": ["jungle", "forest", "tropical", "dense", "wilderness"],
    "swamp": ["swamp", "marsh", "wetland", "bog", "muddy"],
    "lake": ["lake", "pond", "water", "reservoir", "freshwater"],
    "pond": ["pond", "lake", "water", "small", "freshwater"],
    "stream": ["stream", "creek", "brook", "river", "water"],
    "waterfall": ["waterfall", "falls", "cascade", "water", "cliff"],
    "glacier": ["glacier", "ice", "snow", "frozen", "arctic"],
    "volcano": ["volcano", "lava", "eruption", "mountain", "fire"],
    "crater": ["crater", "hole", "depression", "volcano", "impact"],
    "canyon": ["canyon", "gorge", "ravine", "valley", "cliff"],
    "mesa": ["mesa", "plateau", "table", "flat", "rock"],
    "dune": ["dune", "sand", "hill", "desert", "wind"],
    "oasis": ["oasis", "water", "desert", "palm", "green"],
    "reef": ["reef", "coral", "ocean", "underwater", "marine"],
    "kelp": ["kelp", "seaweed", "ocean", "underwater", "marine"],
    "coral": ["coral", "reef", "ocean", "underwater", "marine"],
    "algae": ["algae", "seaweed", "water", "green", "plant"],
    "moss": ["moss", "lichen", "rock", "tree", "green"],
    "fern": ["fern", "plant", "leaf", "green", "forest"],
    "mushroom": ["mushroom", "fungus", "forest", "wood", "organic"],
    "cactus": ["cactus", "succulent", "desert", "plant", "spine"],
    "palm": ["palm", "tree", "tropical", "coconut", "beach"],
    "pine": ["pine", "tree", "evergreen", "conifer", "forest"],
    "oak": ["oak", "tree", "deciduous", "acorn", "forest"],
    "maple": ["maple", "tree", "leaf", "syrup", "forest"],
    "birch": ["birch", "tree", "white", "bark", "forest"],
    "willow": ["willow", "tree", "water", "weeping", "river"],
    "bamboo": ["bamboo", "grass", "tropical", "panda", "asia"],
    "vine": ["vine", "plant", "climbing", "grape", "tendril"],
    "ivy": ["ivy", "vine", "climbing", "wall", "green"],
    "rose": ["rose", "flower", "thorn", "red", "garden"],
    "tulip": ["tulip", "flower", "spring", "bulb", "garden"],
    "daisy": ["daisy", "flower", "white", "yellow", "meadow"],
    "sunflower": ["sunflower", "flower", "yellow", "sun", "tall"],
    "lily": ["lily", "flower", "water", "pond", "white"],
    "orchid": ["orchid", "flower", "tropical", "exotic", "rare"],
    "lavender": ["lavender", "flower", "purple", "herb", "fragrant"],
    "poppy": ["poppy", "flower", "red", "field", "wild"],
    "cactus": ["cactus", "succulent", "desert", "plant", "spine"],
    "aloe": ["aloe", "succulent", "plant", "medicinal", "green"],
    "fern": ["fern", "plant", "leaf", "green", "forest"],
    "moss": ["moss", "lichen", "rock", "tree", "green"],
    "lichen": ["lichen", "moss", "rock", "tree", "fungus"],
    "seaweed": ["seaweed", "algae", "ocean", "marine", "plant"],
    "kelp": ["kelp", "seaweed", "ocean", "marine", "plant"],
    "coral": ["coral", "reef", "ocean", "marine", "animal"],
    "sponge": ["sponge", "ocean", "marine", "porous", "animal"],
    "jellyfish": ["jellyfish", "ocean", "marine", "transparent", "sting"],
    "starfish": ["starfish", "ocean", "marine", "star", "echinoderm"],
    "crab": ["crab", "ocean", "marine", "shell", "crustacean"],
    "lobster": ["lobster", "ocean", "marine", "shell", "crustacean"],
    "shrimp": ["shrimp", "ocean", "marine", "shell", "crustacean"],
    "clam": ["clam", "ocean", "marine", "shell", "mollusk"],
    "oyster": ["oyster", "ocean", "marine", "shell", "pearl"],
    "mussel": ["mussel", "ocean", "marine", "shell", "mollusk"],
    "snail": ["snail", "shell", "garden", "slow", "mollusk"],
    "slug": ["slug", "garden", "slow", "mollusk", "slimy"],
    "worm": ["worm", "soil", "garden", "insect", "segmented"],
    "ant": ["ant", "insect", "colony", "small", "black"],
    "bee": ["bee", "insect", "honey", "pollinator", "yellow"],
    "wasp": ["wasp", "insect", "sting", "yellow", "black"],
    "butterfly": ["butterfly", "insect", "wings", "colorful", "flower"],
    "moth": ["moth", "insect", "wings", "nocturnal", "gray"],
    "beetle": ["beetle", "insect", "shell", "hard", "small"],
    "ladybug": ["ladybug", "insect", "red", "black", "garden"],
    "dragonfly": ["dragonfly", "insect", "wings", "water", "colorful"],
    "mosquito": ["mosquito", "insect", "bite", "small", "flying"],
    "fly": ["fly", "insect", "small", "flying", "annoying"],
    "spider": ["spider", "arachnid", "web", "eight", "legs"],
    "scorpion": ["scorpion", "arachnid", "sting", "desert", "dangerous"],
    "tick": ["tick", "arachnid", "parasite", "small", "blood"],
    "mite": ["mite", "arachnid", "tiny", "parasite", "dust"],
    "centipede": ["centipede", "myriapod", "many", "legs", "fast"],
    "millipede": ["millipede", "myriapod", "many", "legs", "slow"],
}


def expand_synonyms(description):
    """Expand a description with synonyms for universal coverage.

    Example: "water" -> "water, flood, river, lake, ocean, sea, stream"
    """
    words = description.lower().split()
    expanded = []
    for word in words:
        if word in SYNONYMS:
            expanded.extend(SYNONYMS[word])
        else:
            expanded.append(word)
    return " ".join(expanded)
