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


# --- MAPA / SAPCANA -------------------------------------------------------
# Same fortnightly grid as UNICA, but every series is additionally cut by
# Level (country / region / state) and Region. Slices are handed back in the
# exact shape load_wide() returns so the chart layer can stay unaware of
# which source it is drawing.

MAPA_PATH = Path(__file__).resolve().parent.parent / "Database" / "mapa_master.csv"

MAPA_ID_COLS = ["Level", "Region", "Dataset", "Kind", "Period"]

# The same 24-fortnight Apr-Mar axis unica_master.csv uses. MAPA reports for
# five months past March, since Nordeste's Sep-Aug season outlasts the
# reporting year, but the ingest folds those onto the closing fortnight.
# Mirrors Code/mapa_ingest.py.
MAPA_MONTHS = ["Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
               "Jan", "Feb", "Mar"]
MAPA_PERIODS = [f"{m} ({h})" for m in MAPA_MONTHS for h in (1, 2)]

MAPA_REGIONS = [
    ("Brasil", "country", "BR"),
    ("Centro-Sul", "region", "CS"),
    ("Norte", "region", "N"),
    ("Nordeste", "region", "NE"),
]

MAPA_GROUPS = {
    "Production": ["Cana", "Acucar", "Etanol Total"],
    "Anhydrous": [
        "Anidro Producao", "Anidro Entradas", "Anidro Saidas Distrib",
        "Anidro Saidas M.Ext", "Anidro Saidas Outras",
        "Anidro Estoque E.Fisico", "Anidro Estoque E.Disp",
    ],
    "Hydrous": [
        "Hidratado Producao", "Hidratado Entradas", "Hidratado Saidas Distrib",
        "Hidratado Saidas M.Ext", "Hidratado Saidas Outras",
        "Hidratado Estoque E.Fisico", "Hidratado Estoque E.Disp",
    ],
}


def load_mapa():
    return pd.read_csv(MAPA_PATH)


def mapa_year_columns(df):
    return [c for c in df.columns if c not in MAPA_ID_COLS]


def mapa_states(df):
    return sorted(df.loc[df["Level"] == "state", "Region"].unique())


def mapa_period_grid(df):
    """The full fortnightly axis, in season order. The master is grouped by
    series before period, so the order has to come from the calendar rather
    than from the order rows happen to appear in."""
    present = set(df["Period"])
    return [p for p in MAPA_PERIODS if p in present]


def mapa_slice(df, level, region, dataset):
    """One series, reshaped to the [Dataset, Kind, Period, years...] frame
    the chart helpers expect.

    Reindexed onto the full period grid so that a region which reports for
    only part of the season - Centro-Sul goes quiet once its Apr-Mar year
    closes, then files one closing true-up - keeps every year aligned on the
    same rows, with the quiet stretch showing as a genuine gap rather than
    silently closing up. Trailing periods nobody ever reports are dropped so
    the axis ends where the data does."""
    sub = df[(df["Level"] == level)
             & (df["Region"] == region)
             & (df["Dataset"] == dataset)]
    if sub.empty:
        return sub.drop(columns=["Level", "Region"], errors="ignore"), "flow"

    kind = sub["Kind"].iloc[0]
    years = mapa_year_columns(sub)
    grid = mapa_period_grid(df)
    sub = (sub.drop(columns=["Level", "Region"])
              .set_index("Period")
              .reindex(grid)
              .reset_index())
    sub["Dataset"] = dataset
    sub["Kind"] = kind

    keep = sub[years].notna().any(axis=1)
    if keep.any():
        sub = sub.loc[: keep[keep].index.max()]
    return sub[["Dataset", "Kind", "Period"] + years].reset_index(drop=True), kind
