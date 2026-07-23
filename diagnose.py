"""Print how config resolved, and what labels.csv actually contains."""
import os, pandas as pd, config as C

print("env  DATASET         =", os.environ.get("DATASET", "<unset>"))
print("env  C2020_CLASS_SET =", os.environ.get("C2020_CLASS_SET", "<unset>"))
print("env  WORK_DIR        =", os.environ.get("WORK_DIR", "<unset>"))
print()
print("config.DATASET   =", C.DATASET)
print("config.WORK_DIR  =", C.WORK_DIR)
print("config.CLASSES   =", C.CLASSES)

path = os.path.join(C.WORK_DIR, "labels.csv")
df = pd.read_csv(path, index_col="ecg_id", nrows=5)
print("\nlabels.csv       =", path)
print("its columns      =", list(df.columns))

missing = [c for c in C.CLASSES if c not in df.columns]
print("\nmissing from csv =", missing or "none — config and labels.csv agree")
