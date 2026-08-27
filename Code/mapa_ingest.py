"""Turn the MAPA/SAPCANA XLS dump into Database/mapa_master.csv.

Each published report is cumulative from the start of the safra (Periodo
inicial is always 01/04 of the opening year) - only Periodo final moves.
So fortnightly flows are the difference between consecutive reports, while
the ESTOQUE columns are levels and pass through untouched. Diffing the
cumulatives rather than storing them means MAPA's revisions to earlier
fortnights flow through automatically on the next run.

Two things the raw files make awkward, both handled here:

* A safra spans 17 months, not 12. Reports run Apr -> Aug of the following
  year because Nordeste's Sep-Aug season outlasts Centro-Sul's Apr-Mar. The
  trailing five months are labelled 'Apr+' .. 'Aug+' so they never collide
  with the season's own opening April. The first 24 periods line up exactly
  with unica_master.csv's Apr (1) .. Mar (2) axis.

* Column positions move between safras (a 22-column and a 19-column layout
  are both in circulation), so columns are located by reading the sheet's
  own header rows rather than by index. Header text arrives with unreliable
  accent encoding, so matching only ever uses ASCII-safe fragments.

Output shape mirrors unica_master.csv so the dashboard can share code:
    Level,Region,Dataset,Kind,Period,18/19,...,26/27
"""
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DUMP = ROOT / "Database" / "Mapa" / "data dump"
OUT = ROOT / "Database" / "mapa_master.csv"

STOCK_DATASETS = {
    "Anidro Estoque E.Fisico", "Anidro Estoque E.Disp",
    "Hidratado Estoque E.Fisico", "Hidratado Estoque E.Disp",
}

REGION_CODE = {"Centro-Sul": "CS", "Nordeste": "NE", "Norte": "N"}

# 17 months: the Centro-Sul Apr-Mar year, then the Nordeste tail.
MONTHS = ["Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
          "Jan", "Feb", "Mar", "Apr+", "May+", "Jun+", "Jul+", "Aug+"]
PERIODS = [f"{m} ({h})" for m in MONTHS for h in (1, 2)]
PERIOD_ORDER = {p: i for i, p in enumerate(PERIODS)}

DATE_RE = re.compile(r"(\d{2})/(\d{2})/(\d{4})")


def txt(v):
    """Cell as a plain string. Accented characters survive the trip from
    xlrd unreliably, so callers only ever match ASCII-safe fragments."""
    return "" if pd.isna(v) else str(v).strip()


def num(v):
    if pd.isna(v):
        return None
    if isinstance(v, str):
        v = v.replace(".", "").replace(",", ".").strip()
        if not v:
            return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def column_map(df, i):
    """Locate every measure column from the three header rows below a
    'Safra:' banner at row i. Returns {column index: dataset name}."""
    section, group, sub = df.iloc[i + 1], df.iloc[i + 2], df.iloc[i + 3]
    mapping, current = {}, ""
    for col in range(df.shape[1]):
        s, g, u = txt(section[col]), txt(group[col]), txt(sub[col])
        if s:
            current = s
        if g.startswith("Cana"):
            mapping[col] = "Cana"
        elif "ucar" in g:                       # A(c)ucar
            mapping[col] = "Acucar"
        elif g.startswith("Etanol"):
            mapping[col] = "Etanol Total"
        else:
            grade = ("Anidro" if current.startswith("ANIDRO")
                     else "Hidratado" if current.startswith("HIDRATADO") else None)
            if not grade:
                continue
            if g.startswith("Produ"):           # Produ(ca)o
                mapping[col] = grade + " Producao"
            elif g.startswith("Entradas"):
                mapping[col] = grade + " Entradas"
            elif u.startswith("Distrib"):
                mapping[col] = grade + " Saidas Distrib"
            elif u.startswith("M.Ext"):
                mapping[col] = grade + " Saidas M.Ext"
            elif u.startswith("Outras"):
                mapping[col] = grade + " Saidas Outras"
            elif u.startswith("E.F"):           # E.F(is)ico
                mapping[col] = grade + " Estoque E.Fisico"
            elif u.startswith("E.Disp"):
                mapping[col] = grade + " Estoque E.Disp"
    return mapping


def banner(df, i):
    """Read safra / periodo / regiao out of a 'Safra:' header row, wherever
    in the row they happen to sit."""
    joined = " | ".join(txt(c) for c in df.iloc[i] if txt(c))
    safra = re.search(r"Safra:\s*(\d{4})/(\d{4})", joined)
    ini = re.search(r"inicial:\s*(\d{2}/\d{2}/\d{4})", joined)
    fim = re.search(r"final:\s*(\d{2}/\d{2}/\d{4})", joined)
    region = re.search(r"o:\s*(Centro-Sul|Nordeste|Norte)", joined)
    if not (safra and ini and fim):
        return None
    return (safra.group(1)[2:] + "/" + safra.group(2)[2:],
            DATE_RE.match(ini.group(1)).groups(),
            DATE_RE.match(fim.group(1)).groups(),
            REGION_CODE.get(region.group(1)) if region else None)


def period_label(ini, fim):
    """Which fortnight the report closes, counted from Periodo inicial."""
    _, im, iy = (int(x) for x in ini)
    fd, fm, fy = (int(x) for x in fim)
    n = (fy - iy) * 12 + (fm - im)
    if not 0 <= n < len(MONTHS):
        return None
    return "%s (%d)" % (MONTHS[n], 1 if fd <= 15 else 2)


def row_values(df, i, cols):
    return {name: num(df.iat[i, col]) for col, name in cols.items()}


def parse_file(path):
    """-> (safra, period, {(level, region): {dataset: cumulative value}})"""
    df = pd.ExcelFile(path).parse(0, header=None)
    col0 = df[0].map(txt)

    safra = period = None
    cols, blocks = {}, {}
    region, brasil = None, False

    for i, cell in col0.items():
        if cell.startswith("Safra:"):
            info = banner(df, i)
            if not info:
                continue
            safra, ini, fim, region = info
            period = period or period_label(ini, fim)
            cols = cols or column_map(df, i)
        elif cell == "TOTAL BRASIL":
            region, brasil = "BR", True
        elif cell == "Tot." and region:
            level = "country" if brasil and region == "BR" else "region"
            blocks[(level, region)] = row_values(df, i, cols)
            region = None
        elif re.fullmatch(r"[A-Z]{2}", cell) and region:
            blocks[("state", cell)] = row_values(df, i, cols)

    if not (safra and period and blocks):
        raise ValueError("no readable safra/periodo/data block")
    return safra, period, blocks


def regions_in(blocks):
    return {reg for lvl, reg in blocks if lvl == "region"}


def main():
    files = sorted(DUMP.rglob("*.xls"))
    if not files:
        sys.exit("No .xls files under %s - run mapa_fetch.py first." % DUMP)

    cum, bad = {}, []
    for f in files:
        try:
            safra, period, blocks = parse_file(f)
        except Exception as exc:
            bad.append((f.name, "%s: %s" % (type(exc).__name__, exc)))
            continue
        cum.setdefault(safra, {})[period] = blocks

    records = {}
    for safra, by_period in cum.items():
        # A region can drop out of one report and come back in the next (its
        # season ends, or MAPA simply omits it). Differencing against the
        # immediately preceding report would then read the whole season-to-
        # date cumulative as one fortnight's flow, so each entity is carried
        # against the last report it actually appeared in.
        last_cum, last_regions = {}, {}
        for period in sorted(by_period, key=PERIOD_ORDER.get):
            blocks = by_period[period]
            regions = regions_in(blocks)
            for key, vals in blocks.items():
                seen = last_cum.get(key)
                for dataset, value in vals.items():
                    if value is None:
                        continue
                    if dataset not in STOCK_DATASETS:
                        before = (seen or {}).get(dataset)
                        if before is not None:
                            # TOTAL BRASIL shrinks when a region stops being
                            # reported. Differencing across that break would
                            # show the drop as a huge negative flow, so the
                            # aggregate is only differenced while the set of
                            # regions behind it holds steady.
                            if key[0] == "country" and last_regions.get(key) != regions:
                                continue
                            value -= before
                    records.setdefault(key + (dataset, period), {})[safra] = round(value)
                last_cum.setdefault(key, {}).update(
                    {d: v for d, v in vals.items() if v is not None})
                last_regions[key] = regions

    years = sorted({y for r in records.values() for y in r},
                   key=lambda s: int(s[:2]))
    out = pd.DataFrame([
        {"Level": lvl, "Region": reg, "Dataset": ds,
         "Kind": "stock" if ds in STOCK_DATASETS else "flow", "Period": per,
         **{y: vals.get(y) for y in years}}
        for (lvl, reg, ds, per), vals in records.items()
    ])
    out = out.sort_values(
        ["Level", "Region", "Dataset", "Period"],
        key=lambda c: c.map(PERIOD_ORDER) if c.name == "Period" else c,
    )
    out.to_csv(OUT, index=False)

    print("Wrote %s" % OUT)
    print("  %d rows | safras: %s" % (len(out), ", ".join(years)))
    print("  %d files read, %d unreadable" % (len(files), len(bad)))
    for name, err in bad:
        print("    SKIPPED %s - %s" % (name, err))


if __name__ == "__main__":
    main()
