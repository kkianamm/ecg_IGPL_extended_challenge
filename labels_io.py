"""
Single place to read ``labels.csv``, with a preflight check that the file's
columns match the class vocabulary ``config.py`` resolved.

Without this, a mismatch surfaces as a bare pandas ``KeyError: "None of
[Index([...])] are in the [columns]"`` *after* the expensive image-encoding
pass, which says nothing about the actual cause: ``DATASET`` /
``C2020_CLASS_SET`` not matching the run that generated the file.
"""
from __future__ import annotations

import os

import pandas as pd

import config as C


def labels_path() -> str:
    """Path to the label file for the active dataset + class set."""
    return getattr(C, "LABELS_CSV", os.path.join(C.WORK_DIR, "labels.csv"))


def check_columns(df: pd.DataFrame, path: str | None = None) -> None:
    """Raise a diagnostic error if `df` lacks a column for every active class."""
    missing = [c for c in C.CLASSES if c not in df.columns]
    if not missing:
        return

    path = path or labels_path()
    label_cols = [
        c for c in df.columns
        if c not in ("filename", "source", "fs", "sig_len", "report",
                     "superclasses", "strat_fold", "patient_id", "age", "sex")
    ]
    hint = (
        "Regenerate the labels with the same settings you are evaluating "
        "under:\n"
        f"    DATASET={C.DATASET} "
        + (f"C2020_CLASS_SET={C.C2020_CLASS_SET} " if C.DATASET == "challenge2020" else "")
        + ("python challenge2020_data.py"
           if C.DATASET == "challenge2020" else "python prepare_data.py")
    )
    raise SystemExit(
        f"\nLabel/config mismatch.\n\n"
        f"  config.DATASET   = {C.DATASET}\n"
        + (f"  C2020_CLASS_SET  = {C.C2020_CLASS_SET}\n"
           if C.DATASET == "challenge2020" else "")
        + f"  config.CLASSES   = {C.CLASSES}\n"
        f"  labels file      = {path}\n"
        f"  its label columns= {label_cols}\n\n"
        f"Missing from the file: {missing}\n\n"
        f"The file was written by a run with a different class vocabulary.\n"
        f"{hint}\n"
    )


def read_labels(index_col: str = "ecg_id", validate: bool = True) -> pd.DataFrame:
    """Read the active label file, checking it matches ``config.CLASSES``."""
    path = labels_path()
    if not os.path.exists(path):
        raise SystemExit(
            f"\nNo label file at {path}.\n"
            f"Run "
            + ("challenge2020_data.py" if C.DATASET == "challenge2020"
               else "prepare_data.py")
            + f" with DATASET={C.DATASET} first.\n"
        )
    df = pd.read_csv(path, index_col=index_col)
    if validate:
        check_columns(df, path)
    return df


def dataset_label():
    """Human-readable name of the active dataset, for report headers."""
    if getattr(C, "DATASET", "ptbxl") == "challenge2020":
        return f"Challenge 2020 ({len(C.CLASSES)} {C.C2020_CLASS_SET} classes)"
    return "PTB-XL"
