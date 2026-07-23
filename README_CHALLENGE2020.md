# PhysioNet/CinC Challenge 2020 in this repo

This ports the **PhysioNet/Computing in Cardiology Challenge 2020** 12-lead ECG
dataset from `ecgclip5` into this IGPL-extended repo, so it runs through the
*same* pipelines as PTB-XL: zero-shot, linear probe, contrastive fine-tune,
BiomedCoOp, **and** the IPL / COMPOSE tracks that are unique to this repo.

You select the dataset with one environment variable; nothing else changes:

```bash
export DATASET=challenge2020      # everything below targets Challenge 2020
export DATASET=ptbxl              # (default) back to the original PTB-XL flow
```

## What was added / changed

### Ported from `ecgclip5` (unchanged)

| File | Change |
|------|--------|
| `challenge2020_labels.py` | **new** — SNOMED CT tables: the 24 scored classes (27 codes with 3 Challenge-equivalent pairs merged), English descriptions, a BiomedCoOp prompt generator, and an approximate SNOMED→PTB-XL-superclass map. |
| `challenge2020_data.py` | **new** — data prep (the Challenge-2020 analogue of `prepare_data.py`): parses headers, builds labels, makes a stratified split, renders images. |
| `config.py` | dataset switch via `DATASET`; the PTB-XL block is byte-for-byte the old behavior. |
| `prepare_data.py` | `image_path_for` now accepts string record IDs (PTB-XL integer names unchanged). |
| `ecg_prompts.py` | BiomedCoOp falls back to the active dataset's prompts/descriptions when they aren't PTB-XL's. |

### New here — the IPL / COMPOSE track

The IPL and COMPOSE code was written against the 5 PTB-XL superclasses in three
places. Each is now dataset-aware, with the PTB-XL path left byte-for-byte
identical:

| File | Change |
|------|--------|
| `config_ipl.py` | `CLASSNAMES`, `CLASS_PROMPTS` and `LABEL_ALIASES` are derived from `config.CLASSES` / `config.CLASS_DESCRIPTIONS` when `DATASET=challenge2020`. Anchor prompts reuse the generated BiomedCoOp ensemble (first 3 per class). The PTB-XL block is unchanged and sets `LABEL_ALIASES = None` so `data_fix.py` keeps using its own defaults. |
| `ipl/data.py` | `_label_code` now reverse-looks-up `config.CLASS_DESCRIPTIONS` before falling back to `.upper()`, so the human-readable classnames resolve to the `labels.csv` class-code columns (`AF`, `RBBB`, …). |
| `train_compose.py` | `metric_display_names` only enforces the fixed `NORM/MI/STTC/CD/HYP` report contract for PTB-XL; other datasets report their own class codes in `config.CLASSES` order, without reordering columns. |

Untouched, because they already key off `config.CLASSES` / `config_ipl.CLASSNAMES`,
the `strat_fold` split and `work*/labels.csv`: `zero_shot_eval.py`,
`extract_features.py`, `linear_probe.py`, `finetune_clip.py`,
`train_biomedcoop.py`, `evaluation.py`, `train_ipl.py`, `eval_ipl.py`,
`data_fix.py`, `modules/`, `ipl/metrics.py`.

## Why this dataset needs an adapter (and PTB-XL didn't)

1. **Labels are SNOMED CT codes** on a `#Dx:` line in each WFDB `.hea` header,
   not PTB-XL's SCP superclasses. They map to the 24 officially *scored* classes
   (multi-label), merging the three pairs the Challenge scores as identical
   (`CRBBB≡RBBB`, `PAC≡SVPB`, `PVC≡VPB`).
2. **Records vary in sampling rate (257–1000 Hz) and length (6 s – 30 min)**
   across the six source databases. Each record is cropped/padded to a fixed
   window (default 10 s, centered) at its **native** rate before rendering, so
   the ECG images stay comparable. The 30-minute INCART Holter records are
   center-cropped.
3. **There is no official train/val/test split.** A reproducible multi-label
   **iterative-stratified** 10-fold split is written as `strat_fold`, reusing the
   repo's convention (folds 1–8 train, 9 val, 10 test).

## Download the data (~7 GB)

```bash
wget -r -N -c -np https://physionet.org/files/challenge-2020/1.0.1/
```

Extract every source tarball into one folder:

```
data/challenge2020/
  WFDB_CPSC2018/     A*.hea  A*.mat
  WFDB_CPSC2018_2/   Q*.hea  Q*.mat
  WFDB_StPetersburg/ I*.hea  I*.mat
  WFDB_PTB/          S*.hea  S*.mat
  WFDB_PTBXL/        HR*.hea HR*.mat
  WFDB_Ga/           E*.hea  E*.mat
```

Point `DATA_DIR` at that parent folder (headers are found recursively):

```bash
export DATA_DIR=/path/to/data/challenge2020
```

> Note: the records in `WFDB_PTBXL/` are the *same* signals as the standalone
> PTB-XL dataset, just relabeled with SNOMED codes. If you evaluate on both, be
> aware of that overlap.

## Class set

Chosen with `C2020_CLASS_SET` (default `scored`):

- `scored` — the **24** canonical scored classes; multi-label; the native
  Challenge 2020 benchmark. Metric: macro AUROC/AUPRC over the 24 classes.
- `superclass` — the **5 PTB-XL superclasses** (`NORM/MI/STTC/CD/HYP`) via an
  approximate SNOMED map, for rough cross-dataset comparison with PTB-XL. That
  map draws on scored *and* unscored codes (MI and hypertrophy are not in the
  scored set) and is intentionally partial — use it for comparison, not as
  clinical ground truth.

Other knobs (env vars): `C2020_WINDOW_SECONDS` (default 10), `C2020_SPLIT_SEED`
(default 42), `WORK_DIR` (default `./work_challenge2020`).

## Run it

```bash
export DATASET=challenge2020
export DATA_DIR=/path/to/data/challenge2020

# 1) Prepare labels + render images (replaces prepare_data.py for C2020)
python challenge2020_data.py --limit 500     # quick smoke test first
python challenge2020_data.py                 # full run

# 2) Base pipelines — identical to the PTB-XL instructions
python zero_shot_eval.py --task multi
python extract_features.py && python linear_probe.py
python finetune_clip.py
python train_biomedcoop.py --shots 16 --seed 1 --task multi

# 3) IPL / COMPOSE — also unchanged
python train_ipl.py --phase C --shots 16 --seed 1
python train_compose.py --exp <experiment-name> --shots 16 --seed 1
```

`challenge2020_data.py` writes `work_challenge2020/labels.csv` (columns
`ecg_id, filename, source, fs, sig_len, report, superclasses`, one 0/1 column per
class, and `strat_fold`) plus `work_challenge2020/images/<record>.png` — the
exact contract the rest of the repo expects. `config_ipl.py` picks up
`WORK_DIR` from `config.py`, so `LABELS_CSV`, `IMAGE_DIR`, `CKPT_DIR` and
`CACHE_DIR` all follow automatically.

## Notes & caveats

- **`data_fix._guard` is strict.** It raises if any class has zero positives in
  a split. With 24 classes the rarest ones (e.g. `Brady`, `LPR`) are thin, so if
  you subset the data heavily — `--limit`, small `--shots`, or an unlucky seed —
  expect that error. Run the full dataset, or switch to
  `C2020_CLASS_SET=superclass`, before reading anything into it.
- **Single-label mode** (`--task single`) filters to records with exactly one
  active class. With 24 multi-label classes those subsets are small and some rare
  classes may have too few examples for large `--shots`; multi-label is the
  primary protocol here.
- **DGA's semantic-hierarchy branch** (`use_semantic_hierarchy=True`) is still
  the single-label PTB-XL tree and already raises `NotImplementedError`. It is
  not wired for the 24-class vocabulary either; leave it off.
- **Zero-shot expectations** match the PTB-XL README: BiomedCLIP was never
  trained on ECG plots, so zero-shot over 24 classes will be modest. Linear
  probe, fine-tuning and prompt learning improve substantially.
- **Patient overlap**: most sources are one record per patient; INCART's 74
  records come from 32 patients, so a little within-source leakage across folds
  is possible there. The split is record-level (standard for this dataset).
- The split and rendering are deterministic given `C2020_SPLIT_SEED` and
  `C2020_WINDOW_SECONDS`.

## Troubleshooting: `KeyError: "None of [Index([...])] are in the [columns]"`

This means `config.CLASSES` and the label file disagree — the CSV was written by
a run with a different class vocabulary. Run `python diagnose.py` to see which.
The two causes:

- **`DATASET` not exported in this shell.** `config.py` falls back to `ptbxl`,
  so `CLASSES` becomes `NORM/MI/STTC/CD/HYP` while `WORK_DIR` still points at the
  Challenge 2020 work directory. Fix: `export DATASET=challenge2020`.
- **`C2020_CLASS_SET` changed after preparing the data.** The `scored` and
  `superclass` vocabularies are different column sets.

Both now fail immediately with a diagnostic instead of a bare pandas `KeyError`
after the image-encoding pass, and the two Challenge 2020 class sets write to
separate files (`labels.csv` and `labels_superclass.csv`) inside one shared
`WORK_DIR`, so switching between them never invalidates existing work. The
rendered images are shared — you never re-render 43k records to change class set.
