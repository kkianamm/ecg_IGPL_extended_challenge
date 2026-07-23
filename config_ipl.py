"""
IPL configuration. Kept separate from your existing config.py so nothing
in the base repo changes. Paths fall back to your config.py / env vars.
"""

import os

# ---- paths (reuse your repo's config if importable) -----------------------
try:
    import config as base  # your existing config.py
    WORK_DIR = getattr(base, "WORK_DIR", "work")
    LABELS_CSV = getattr(base, "LABELS_CSV", os.path.join(WORK_DIR, "labels.csv"))
    IMAGE_DIR = getattr(base, "IMAGE_DIR", os.path.join(WORK_DIR, "images"))
except Exception:
    WORK_DIR = os.environ.get("WORK_DIR", "work")
    LABELS_CSV = os.path.join(WORK_DIR, "labels.csv")
    IMAGE_DIR = os.path.join(WORK_DIR, "images")

CKPT_DIR = os.path.join(WORK_DIR, "checkpoints")
CACHE_DIR = os.path.join(WORK_DIR, "feat_cache")

# ---- active dataset -------------------------------------------------------
# 'ptbxl' (default) keeps the original 5-superclass setup byte-for-byte.
# 'challenge2020' derives the class vocabulary from config.py / the SNOMED
# tables in challenge2020_labels.py, so IPL/COMPOSE run unchanged on it.
try:
    DATASET = getattr(base, "DATASET", "ptbxl")
except Exception:
    DATASET = os.environ.get("DATASET", "ptbxl")

if DATASET == "ptbxl":
    # ---- the 5 PTB-XL diagnostic superclasses ----------------------------
    # Order defines the target column order everywhere.
    CLASSNAMES = [
        "normal ecg",
        "myocardial infarction",
        "st t wave change",
        "conduction disturbance",
        "hypertrophy",
    ]

    # Human-readable anchor prompts (ensembled) for the frozen zero-shot text
    # used in the Phase-B anchor loss. Add/adjust freely.
    CLASS_PROMPTS = [
        ["a twelve lead ecg showing a normal heart rhythm",
         "an electrocardiogram with no abnormality",
         "normal ecg"],
        ["a twelve lead ecg showing myocardial infarction",
         "an electrocardiogram indicating a heart attack",
         "ecg with signs of myocardial infarction"],
        ["a twelve lead ecg showing st and t wave changes",
         "an electrocardiogram with st/t wave abnormality",
         "ecg with st-t changes"],
        ["a twelve lead ecg showing a conduction disturbance",
         "an electrocardiogram with a bundle branch block",
         "ecg with conduction abnormality"],
        ["a twelve lead ecg showing ventricular hypertrophy",
         "an electrocardiogram indicating hypertrophy",
         "ecg with hypertrophy"],
    ]

    # data_fix.py falls back to its own DEFAULT_ALIASES for PTB-XL.
    LABEL_ALIASES = None

else:  # challenge2020
    # config.py already resolved CLASSES / CLASS_DESCRIPTIONS for the active
    # C2020_CLASS_SET ('scored' -> 24 classes, 'superclass' -> 5 PTB-XL ones).
    if "base" not in dir():
        raise ImportError(
            "DATASET=challenge2020 requires config.py to be importable "
            "(it defines CLASSES / CLASS_DESCRIPTIONS for the active class set)."
        )
    _CODES = list(base.CLASSES)
    _DESC = dict(base.CLASS_DESCRIPTIONS)

    # CLASSNAMES stay human-readable (that is what the prompt learner tokenises);
    # LABEL_ALIASES below is what maps them back to the labels.csv columns.
    CLASSNAMES = [_DESC[c] for c in _CODES]

    # Anchor prompts: reuse the generated BiomedCoOp ensemble when config.py
    # built one, otherwise fall back to three simple templates per class.
    _generated = getattr(base, "BIOMEDCOOP_TEMPLATES", None) or {}
    CLASS_PROMPTS = [
        list(_generated.get(code, []))[:3] or [
            f"a twelve lead ecg showing {_DESC[code]}",
            f"an electrocardiogram with {_DESC[code]}",
            _DESC[code],
        ]
        for code in _CODES
    ]

    # Aliases aligned to CLASSNAMES order: labels.csv carries one 0/1 column per
    # class *code* (e.g. 'AF'), while CLASSNAMES are the descriptions.
    LABEL_ALIASES = [
        sorted({code, code.lower(), _DESC[code], _DESC[code].lower()})
        for code in _CODES
    ]

# ---- IPL hyper-parameters -------------------------------------------------
N_CTX = 8
CTX_INIT = "this is a twelve lead ecg showing"

# Phase presets mirror IGPL's A/B/C staging.
PHASES = {
    "A": dict(use_metanet=False, lambda_anchor=0.0),   # CoOp: learnable prompt only
    "B": dict(use_metanet=False, lambda_anchor=1.0),   # + text-anchor preservation
    "C": dict(use_metanet=True,  lambda_anchor=1.0),   # + instance-conditioned prompt (full IPL)
}

# ---- training -------------------------------------------------------------
LR = 2e-3
WEIGHT_DECAY = 1e-4
EPOCHS = 50
BATCH_SIZE = 64
NUM_WORKERS = 8
THRESHOLD = 0.5
