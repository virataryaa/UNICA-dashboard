# Brazil Sugar

Two independent readings of the Brazilian cane crop in one Streamlit app:
**UNICA**'s mill survey and the Ministry of Agriculture's **MAPA/SAPCANA**
filings, plus a page that compares them.

Deploys from `main` to Streamlit Cloud. Pushing to `main` is a release.

---

## Quick start

```bash
cd Dashboard
pip install -r requirements.txt
streamlit run app.py
```

**Two buttons, one per source — double-click whichever you need:**

| Button | What it does |
|---|---|
| `Update MAPA.bat` | Downloads any new reports from gov.br, rebuilds `mapa_master.csv`, pushes it |
| `Update UNICA.bat` | Checks `unica_master.csv` and pushes it. **Downloads nothing** — UNICA is kept by hand |

Both refuse to run off `main` — Streamlit deploys only from `main`, so a push
from anywhere else would report success while nothing went live. Each commit
names its one CSV explicitly, so nothing else in the working tree can ride
along into a data release. If gov.br is unreachable, `Update MAPA` warns and
carries on with the reports already on disk. Pass `/nopause` to run either
from Task Scheduler.

The steps by hand, from the repo root:

```bash
python Cleansing/mapa_fetch.py    # all safras; add e.g. 2026-2027 to limit
python Cleansing/mapa_ingest.py   # rebuilds Database/mapa_master.csv
python Cleansing/validate_csv.py  # checks Database/unica_master.csv
```

`mapa_fetch.py` skips files already on disk, so a routine run pulls only the
newest fortnight. `mapa_ingest.py` always rebuilds the whole CSV from every
file in the dump — it is not incremental, which is what lets MAPA's revisions
to earlier fortnights flow through on the next run.

---

## Layout

```
Update MAPA.bat        download + rebuild + publish MAPA
Update UNICA.bat       check + publish UNICA
Cleansing/
  mapa_fetch.py        scrape + download MAPA XLS from gov.br
  mapa_ingest.py       XLS dump -> Database/mapa_master.csv
  validate_csv.py      schema checks on unica_master.csv
Dashboard/
  app.py               pages, routing, sidebar
  charts.py            plotly builders + the stats behind them
  table_html.py        hand-rolled HTML tables (not st.dataframe)
  data_loader.py       CSV loading, slicing, the UNICA/MAPA date axis
Database/
  unica_master.csv     UNICA, published
  mapa_master.csv      MAPA, published
  Mapa/data dump/      raw XLS, gitignored (~12 MB, 283 files)
```

`Dashboard/` and `Database/` must stay where they are: Streamlit Cloud runs
`Dashboard/app.py`, and the app reads `../Database/`.

## Navigation

```
Brazil Sugar
├── UNICA          Overview + 12 series (6 fortnightly, 6 monthly)
├── MAPA           Overview + 17 series, any region or state
└── MAPA vs UNICA  both sources through time, agreement scatters
```

The **region selector lives in the sidebar** and is enabled only on the MAPA
pages. It is disabled with a stated reason on the UNICA pages (UNICA reports
Centro-Sul only) and on the comparison (fixed to Centro-Sul, since UNICA has
no Norte or Nordeste to compare against). A disabled picker never rewrites the
selection it is showing, so leaving a MAPA page does not reset your region.

---

## Data

### `unica_master.csv`

`Dataset,Kind,Period,16/17…26/27` — `Kind` is `flow` or `ratio`.

Nine series come straight from UNICA. Three are computed in `app.py` (`DERIVED`):

| Derived | Formula |
|---|---|
| Fuel Consumption | `Hydrous × 0.7 + Anhydrous ÷ 0.3` |
| Gasolina Consumption | `Anhydrous ÷ 0.27` |
| Hydrous Share | `Hydrous × 0.7 ÷ Fuel × 100` |

UNICA publishes fortnightly flows directly — no differencing needed.
`Anhydrous (Int)`, `Hydrous (Int)`, `Ethanol Sales` and the three derived
series are **monthly**; the rest are fortnightly.

### `mapa_master.csv`

`Level,Region,Dataset,Kind,Period,18/19…26/27` — 11,016 rows =
17 datasets × 27 entities × 24 fortnights. `Kind` is `flow` or `stock`.

- **Entities:** Brasil (`country/BR`), Centro-Sul / Norte / Nordeste
  (`region/CS|N|NE`), and 23 states (`state/<UF>`). All are **read from rows in
  the file** — we never sum states into a region.
- **Coverage:** XLS exists from safra 18/19. 16/17 and 17/18 are PDF-only.
- **Units:** cane and sugar in tonnes, everything else in m³.

All 17 series come from columns in the sheet. Nothing is invented — but only
the four `Estoque` series are as-published:

| Treatment | Series |
|---|---|
| **Differenced** (13) | Cana, Acucar, Etanol Total, and for each grade: Producao, Entradas, Saidas Distrib / M.Ext / Outras |
| **As-is, levels** (4) | Anidro/Hidratado Estoque E.Fisico and E.Disp |

`Etanol Total` = `Anidro Producao` + `Hidratado Producao` exactly.

---

## Why MAPA, alongside UNICA

- Covers **every mill in Brazil**, not just UNICA's Centro-Sul membership
- Publishes **stocks and movements** (E.Fisico, E.Disp, Entradas, Saidas to
  distributors / exports / other) that UNICA does not report at all
- Lands roughly **one fortnight ahead** of UNICA

The cost is that every MAPA flow is a computed difference, so one bad print
contaminates two fortnights.

---

## The MAPA source, and the traps in it

Plain static files on gov.br — no login, no session. One listing page per
safra at `.../agroenergia/acompanhamento-da-producao-sucroalcooleira/<YYYY-YYYY>`.

Filenames are inconsistent between and within safras (`_2` suffixes, `.PDF` vs
`.pdf`), so **URLs are scraped, never constructed**. Two sheet layouts are in
circulation (22-column and 19-column), so columns are located by reading the
sheet's own header rows rather than by index; accents arrive mangled from
`xlrd`, so header matching uses only ASCII-safe fragments (`Produ`, `ucar`,
`E.F`).

Everything below is handled in `Cleansing/mapa_ingest.py`. Each one produced a
visible, wrong number before it was.

**1. Reports are cumulative, not fortnightly.**
Periodo inicial is always 01/04; only Periodo final moves. Fortnightly flows
are the difference between consecutive reports. Stocks are levels and pass
through. Differencing rather than storing cumulatives is what makes MAPA's
revisions self-correct on the next run.

**2. A safra spans 17 months, not 12.**
Reporting runs Apr through Aug of the following year, because Nordeste's
Sep–Aug season outlasts Centro-Sul's Apr–Mar one — hence ~34 files per safra.
Tail periods are read on their own `Apr+ (1)` … `Aug+ (2)` axis so they never
collide with the season's opening months, then folded onto `Mar (2)`. Every
region therefore ends on the same **24-period axis as UNICA**.

**3. Regions drop out once their season closes.**
This shrinks the TOTAL BRASIL row and leaves mid-series gaps. Entities are
differenced against the last report they actually appeared in, not `n-1`.
Getting this wrong produced exact-2× season totals and a −578M phantom flow.

**4. Some files carry a Periodo final that contradicts the report inside.**
15/11/2022 is stamped 30/11; 31/05/2019 is stamped 15/06. Each collides with
the genuine report for that fortnight. Resolved by cumulative size: the larger
reading closes the fortnight, the shorter belongs to the preceding slot and
moves there if free. **8 fortnights** have such clashes. This is what made
22/23 look like it was missing a `Nov (1)` print — it was not.

**5. Two population changes are not flows, and record nothing.**
TOTAL BRASIL shrinking when a region stops being reported; and every new April,
where the report stops counting units that have opened the next safra (its own
footnote says so), which drags all Nordeste cumulatives down. Smaller negatives
**are** kept — they are MAPA revising a prior fortnight down, and dropping them
breaks the season total.

**6. Some safras close with a full-season restatement filed months late.**
18/19 and 21/22 both arrive the following August — past the April reset that
puts every entity onto a smaller basis. The fix carries **two bases** past the
rollover, told apart by the season's closing cumulative frozen at the first
drop, so the restatement is differenced against the season basis and the tail
against itself. The threshold must be the frozen close rather than the running
figure: MAPA prints the odd tail reading it reverses next report, and only a
fixed threshold keeps both halves on one basis where they cancel.

*Fixed 2026-09-04. Before it, 18/19 `Mar (2)` cane read **587,066,209 t** and
the season totalled 1.20 bn against ~640 m for every other year. Every dataset
was affected, sugar included.*

---

## Validation status

**Externally checked (once).** The Aug (1) 26/27 fortnight matched an
independent third-party table exactly on all eight line items — Centro-Sul and
North-Northeast, cane / sugar / anhydrous / hydrous.

**Internal reconciliation.** Summed fortnightly flows equal MAPA's own season
cumulative *exactly* on 24 of 27 country series. The three residuals:
18/19 cane +15,865 t, 18/19 sugar +1,420 t, and **24/25 total ethanol
−64,282 m³ (0.17%) — unexplained, never chased**.

**Cross-source.** UNICA vs MAPA Centro-Sul over the whole record:

| | r | Season-total gap |
|---|---|---|
| Cane | 0.9972 | +0.03% |
| Sugar | 0.9976 | +0.08% |
| Ethanol | 0.9953 | −0.77% |

**Not validated against anything external:** state-level figures, the four
stock series, and the Nordeste post-March tail.

---

## Known issues

- **MAPA ethanol includes corn.** Roughly 17% of Centre-South ethanol. The XLS
  has no feedstock dimension at all, so the split cannot be recovered from this
  source. Consequence: *ethanol per tonne of cane is not a valid yield from
  MAPA data* — the numerator includes corn, the denominator is cane only, and
  the corn share is growing. Sugar per tonne of cane is fine.
- **Anhydrous and hydrous are excluded from the comparison page.** UNICA
  publishes them monthly against MAPA's fortnights; they cannot share the axis
  without resampling one side.
- **Nordeste `Mar (2)` looks huge on movement series** (100×–280× the fortnight
  median). That is trap 2 working as designed — five months folded into one
  bucket — not an error.
- **`use_container_width` is past its removal date** across the whole app. Still
  working; a Streamlit upgrade could break it broadly.
- **Neither button is on Task Scheduler.** Refresh is manual; both take
  `/nopause` so they can be scheduled.
- **gov.br is intermittently unreachable** from the ETG network — DNS resolves
  but TCP 443 times out, sometimes for hours. Other Brazilian sites are fine.
  Retry later rather than debugging the scraper.

## Data currency

`mapa_master.csv` and `unica_master.csv` can drift apart. MAPA is downloaded
by `Update MAPA.bat`; **UNICA is not** — `unica_master.csv` is maintained by
hand, and `Update UNICA.bat` only checks and publishes it. The app's front
page shows how far each source reaches and when each was last pulled, which is
the fastest way to spot a stale side.

As of 2026-09-18: MAPA through `Aug (2) 26/27`; UNICA through `Jun (2) 26/27`,
last edited 7 Aug — four fortnights behind.
