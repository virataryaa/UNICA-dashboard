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

# --- UNICA vs MAPA, on a real-date axis -----------------------------------
# The two masters share the 24-fortnight Apr-Mar grid, but a comparison that
# runs across seasons needs a continuous axis, so each (safra, period) is
# resolved to the calendar date the fortnight closes on. Apr-Dec sit in the
# opening year, Jan-Mar in the closing one.

# UNICA name, MAPA name, unit. Anhydrous and hydrous are deliberately absent:
# UNICA publishes them monthly against MAPA's fortnights, so they cannot be
# compared on this axis without resampling one side.
SOURCE_PAIRS = [
    ("Sugarcane Crush", "Cana", "MT"),
    ("Sugar", "Acucar", "MT"),
    ("Ethanol", "Etanol Total", "m3"),
]


def period_date(safra, period):
    """('18/19', 'Apr (1)') -> date(2018, 4, 15). Returns None for anything
    off the fortnightly grid, so callers can skip UNICA's monthly series."""
    import calendar
    from datetime import date
    try:
        month, half = period.split(" (")
        half = int(half.rstrip(")"))
    except (ValueError, AttributeError):
        return None
    if month not in MAPA_MONTHS:
        return None
    num = MAPA_MONTHS.index(month) + 4
    year = 2000 + int(safra[:2])
    if num > 12:
        num -= 12
        year += 1
    day = 15 if half == 1 else calendar.monthrange(year, num)[1]
    return date(year, num, day)


def source_compare_frame(unica_wide, mapa_wide, unica_name, mapa_name):
    """One tidy frame of date / unica / mapa for a single product, covering
    every season either source publishes. Periods missing on one side stay as
    NaN rather than being dropped, so the charts show where MAPA's coverage
    starts rather than silently closing the gap."""
    u = dataset_slice(unica_wide, unica_name).set_index("Period")
    m, _ = mapa_slice(mapa_wide, "region", "CS", mapa_name)
    m = m.set_index("Period")
    uy, my = year_columns(unica_wide), mapa_year_columns(mapa_wide)

    rows = []
    for safra in sorted(set(uy) | set(my), key=lambda s: int(s[:2])):
        for period in MAPA_PERIODS:
            d = period_date(safra, period)
            if d is None:
                continue
            uv = u[safra].get(period) if safra in uy and period in u.index else None
            mv = m[safra].get(period) if safra in my and period in m.index else None
            if pd.isna(uv) and pd.isna(mv):
                continue
            rows.append({"date": d, "safra": safra, "period": period,
                         "unica": pd.to_numeric(uv, errors="coerce"),
                         "mapa": pd.to_numeric(mv, errors="coerce")})
    return pd.DataFrame(rows)
