"""Registry of SAM assistants (one per context).

All repo IDs below were verified to exist on HuggingFace and to load with
`transformers` (Sam2Model/Sam2Processor for arch "sam2",
SamModel/SamProcessor for arch "sam").
"""

SAM_ASSISTANTS = {
    "general-tiny": {
        "key": "general-tiny",
        "name": "Generaliste · Rapide",
        "repo": "facebook/sam2.1-hiera-tiny",
        "arch": "sam2",
        "context": "Nature · Animaux · Objets",
        "size": "~155 Mo",
        "device_hint": "CPU ok, GPU ideal",
        "description": (
            "SAM 2.1 Tiny : le meilleur compromis vitesse/qualite. "
            "Premier choix pour photos nature, animaux et objets courants. "
            "Fonctionne sur CPU (quelques secondes) et GPU (~0.2 s)."),
    },
    "general-small": {
        "key": "general-small",
        "name": "Generaliste · Equilibre",
        "repo": "facebook/sam2.1-hiera-small",
        "arch": "sam2",
        "context": "Nature · Animaux · Objets",
        "size": "~185 Mo",
        "device_hint": "GPU conseille",
        "description": (
            "SAM 2.1 Small : un cran plus precis que Tiny pour les petits "
            "objets et les contours fins. GPU conseille."),
    },
    "general-base": {
        "key": "general-base",
        "name": "Generaliste · Precis",
        "repo": "facebook/sam2.1-hiera-base-plus",
        "arch": "sam2",
        "context": "Nature · Animaux · Objets",
        "size": "~325 Mo",
        "device_hint": "GPU conseille",
        "description": (
            "SAM 2.1 Base+ : haute precision sur scenes complexes. "
            "GPU conseille, CPU lent."),
    },
    "general-large": {
        "key": "general-large",
        "name": "Generaliste · Maximum",
        "repo": "facebook/sam2.1-hiera-large",
        "arch": "sam2",
        "context": "Nature · Animaux · Objets",
        "size": "~900 Mo",
        "device_hint": "GPU requis",
        "description": (
            "SAM 2.1 Large : la meilleure qualite de masque. "
            "GPU requis, telechargement ~900 Mo."),
    },
    "medical-medsam": {
        "key": "medical-medsam",
        "name": "Medical (MedSAM)",
        "repo": "wanglab/medsam-vit-base",
        "arch": "sam",
        "context": "Medical · Microscopie",
        "size": "~375 Mo",
        "device_hint": "GPU conseille",
        "description": (
            "MedSAM : SAM affiné sur imagerie medicale (IRM, CT, radio, "
            "endoscopie). Privilegier les prompts BOITE : MedSAM a ete "
            "entraine sur boites englobantes."),
    },
}

DEFAULT_ASSISTANT = "general-tiny"


def get_assistant(key):
    """Return the registry entry for key, falling back to default."""
    if key in SAM_ASSISTANTS:
        return SAM_ASSISTANTS[key]
    return SAM_ASSISTANTS[DEFAULT_ASSISTANT]


_ARCH_BY_CLASS = {
    "sammodel": "sam",
    "sam2model": "sam2",
    "sam2videomodel": "sam2",
}

_ARCH_CACHE = {}


def detect_arch(repo, default="sam2"):
    """Detect the checkpoint architecture from its own config.json.

    Returns "sam" or "sam2". The registry value is only a fallback: a stale
    `model_id` in parameters.json can point a "sam" assistant at a sam2
    checkpoint (or the reverse), and the processors are not
    interchangeable -- SamProcessor reads `size["longest_edge"]` while sam2
    checkpoints ship `size: {height, width}`.
    """
    if repo in _ARCH_CACHE:
        return _ARCH_CACHE[repo]
    arch = default
    try:
        import json
        from huggingface_hub import hf_hub_download
        try:
            path = hf_hub_download(repo, "config.json")
        except Exception:
            from huggingface_hub import try_to_load_from_cache
            path = try_to_load_from_cache(repo, "config.json")
        if path:
            with open(path, encoding="utf-8") as f:
                cfg = json.load(f)
            for key in ("architectures", "model_type"):
                value = cfg.get(key)
                if isinstance(value, str):
                    value = [value]
                for name in value or []:
                    found = _ARCH_BY_CLASS.get(str(name).lower())
                    if found:
                        arch = found
                        raise StopIteration
    except StopIteration:
        pass
    except Exception:
        pass
    _ARCH_CACHE[repo] = arch
    return arch


def list_assistants():
    return [SAM_ASSISTANTS[k] for k in SAM_ASSISTANTS]


def assistant_cache_status(repo):
    """Check local HF cache without network. Returns (downloaded, size_mb)."""
    try:
        from huggingface_hub import try_to_load_from_cache
        for filename in ("model.safetensors", "pytorch_model.bin"):
            path = try_to_load_from_cache(repo, filename)
            if path is not None:
                import os
                return (True, round(os.path.getsize(path) / 1e6, 1))
        cfg = try_to_load_from_cache(repo, "config.json")
        if cfg is not None:
            return (False, 0.0)  # metadata only, weights missing
        return (False, 0.0)
    except Exception:
        return (False, 0.0)
