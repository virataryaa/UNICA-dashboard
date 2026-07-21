import pandas as pd
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent.parent / "Database" / "unica_master.csv"

ID_COLS = ["Dataset", "Kind", "Period"]


def load_wide():
    df = pd.read_csv(DATA_PATH)
    return df


def load_long(df_wide=None):
    df = df_wide if df_wide is not None else load_wide()
    year_cols = [c for c in df.columns if c not in ID_COLS]
    long_df = df.melt(id_vars=ID_COLS, value_vars=year_cols, var_name="Year", value_name="Value")
    long_df["Value"] = pd.to_numeric(long_df["Value"], errors="coerce")
    return long_df.dropna(subset=["Value"])


def year_columns(df_wide):
    return [c for c in df_wide.columns if c not in ID_COLS]


def dataset_slice(df_wide, dataset):
    sub = df_wide[df_wide["Dataset"] == dataset].reset_index(drop=True)
    return sub


def dataset_registry(df_wide):
    reg = df_wide[["Dataset", "Kind"]].drop_duplicates().reset_index(drop=True)
    return reg
