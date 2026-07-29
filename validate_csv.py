"""Sanity-checks Database/unica_master.csv before it gets pushed.

Run standalone: python validate_csv.py
Exit code 0 = safe to push. Exit code 1 = problems found, do not push.
"""
import sys
from pathlib import Path

import pandas as pd

CSV_PATH = Path(__file__).resolve().parent / "Database" / "unica_master.csv"

BIWEEKLY_PERIODS = [
    "Apr (1)", "Apr (2)", "May (1)", "May (2)", "Jun (1)", "Jun (2)",
    "Jul (1)", "Jul (2)", "Aug (1)", "Aug (2)", "Sep (1)", "Sep (2)",
    "Oct (1)", "Oct (2)", "Nov (1)", "Nov (2)", "Dec (1)", "Dec (2)",
    "Jan (1)", "Jan (2)", "Feb (1)", "Feb (2)", "Mar (1)", "Mar (2)",
]
MONTHLY_PERIODS = [
    "Apr", "May", "Jun", "Jul", "Aug", "Sep",
    "Oct", "Nov", "Dec", "Jan", "Feb", "Mar",
]

# name -> (kind, period set)
EXPECTED_DATASETS = {
    "Sugarcane Crush": ("flow", BIWEEKLY_PERIODS),
    "Sugar": ("flow", BIWEEKLY_PERIODS),
    "Ethanol": ("flow", BIWEEKLY_PERIODS),
    "ATR": ("flow", BIWEEKLY_PERIODS),
    "ATR Yield": ("ratio", BIWEEKLY_PERIODS),
    "Sugar Mix": ("ratio", BIWEEKLY_PERIODS),
    "Ethanol Sales": ("flow", MONTHLY_PERIODS),
    "Hydrous (Int)": ("flow", MONTHLY_PERIODS),
    "Anhydrous (Int)": ("flow", MONTHLY_PERIODS),
    # Fuel Consumption, Gasolina Consumption, Hydrous Share are derived
    # on the fly by the dashboard from the datasets above — not stored here.
}

ID_COLS = ["Dataset", "Kind", "Period"]


def main():
    errors = []
    warnings = []

    if not CSV_PATH.exists():
        print(f"FAIL: {CSV_PATH} does not exist.")
        return 1

    try:
        df = pd.read_csv(CSV_PATH)
    except Exception as e:
        print(f"FAIL: could not parse CSV - {e}")
        return 1

    for col in ID_COLS:
        if col not in df.columns:
            errors.append(f"Missing required column '{col}'.")
    if errors:
        _report(errors, warnings)
        return 1

    year_cols = [c for c in df.columns if c not in ID_COLS]
    if not year_cols:
        errors.append("No year columns found (everything after Dataset/Kind/Period).")
    for y in year_cols:
        parts = y.split("/")
        if len(parts) != 2 or not all(p.isdigit() and len(p) == 2 for p in parts):
            errors.append(f"Year column '{y}' doesn't look like 'NN/NN' - check for a typo or Excel auto-formatting it into a date.")

    # Duplicate (Dataset, Period) rows
    dupes = df[df.duplicated(subset=["Dataset", "Period"], keep=False)]
    if not dupes.empty:
        for _, row in dupes.iterrows():
            errors.append(f"Duplicate row: Dataset='{row['Dataset']}', Period='{row['Period']}'.")

    # Per-dataset checks
    present_datasets = set(df["Dataset"].unique())
    for name, (kind, periods) in EXPECTED_DATASETS.items():
        if name not in present_datasets:
            warnings.append(f"Expected dataset '{name}' not found in CSV.")
            continue
        sub = df[df["Dataset"] == name]

        bad_kind = sub[sub["Kind"] != kind]
        if not bad_kind.empty:
            errors.append(f"'{name}': expected Kind='{kind}' but found {sorted(bad_kind['Kind'].unique())}.")

        actual_periods = sub["Period"].tolist()
        if actual_periods != periods:
            missing = [p for p in periods if p not in actual_periods]
            extra = [p for p in actual_periods if p not in periods]
            if missing:
                errors.append(f"'{name}': missing period rows {missing}.")
            if extra:
                errors.append(f"'{name}': unexpected period rows {extra} (typo in Period text?).")
            if not missing and not extra:
                errors.append(f"'{name}': periods present but out of order - {actual_periods}.")

        if sub[sub["Dataset"] == name].shape[0] != len(periods):
            pass  # already covered by missing/extra checks above

    unexpected_datasets = present_datasets - set(EXPECTED_DATASETS)
    if unexpected_datasets:
        warnings.append(f"Dataset(s) in CSV not in the known list (new dataset? fine if intentional): {sorted(unexpected_datasets)}")

    # Numeric parseability of all non-blank cells
    for y in year_cols:
        col = df[y]
        non_blank = col.dropna()
        non_numeric = non_blank[pd.to_numeric(non_blank, errors="coerce").isna()]
        if not non_numeric.empty:
            bad_rows = df.loc[non_numeric.index, ["Dataset", "Period"]]
            for _, r in bad_rows.iterrows():
                errors.append(f"Non-numeric value in column '{y}' for Dataset='{r['Dataset']}', Period='{r['Period']}'.")

    # Flag a whole dataset+year column being entirely blank (possible accidental clear)
    for name in present_datasets:
        sub = df[df["Dataset"] == name]
        for y in year_cols:
            if sub[y].notna().sum() == 0:
                warnings.append(f"'{name}' has zero values in column '{y}' - fine if that year hasn't started yet, worth a second look otherwise.")

    return _report(errors, warnings)


def _report(errors, warnings):
    if warnings:
        print("Warnings (won't block the push):")
        for w in warnings:
            print(f"  - {w}")
        print()
    if errors:
        print("FAIL - fix these before pushing:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("PASS - CSV looks good.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
