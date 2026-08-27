"""Download MAPA/SAPCANA 'Acompanhamento da producao' XLS reports.

The gov.br pages expose the reports as plain static files - no login, no
session. Filenames are inconsistent between safras (and even within one),
so we scrape each safra's listing page for .xls hrefs instead of trying to
construct URLs. Files already on disk are skipped, so a routine run only
pulls the newest fortnight.
"""
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin

import requests

BASE = ("https://www.gov.br/agricultura/pt-br/assuntos/sustentabilidade/"
        "agroenergia/acompanhamento-da-producao-sucroalcooleira")

# 16/17 and 17/18 publish PDFs only - XLS coverage starts at 18/19.
SAFRAS = ["2018-2019", "2019-2020", "2020-2021", "2021-2022", "2022-2023",
          "2023-2024", "2024-2025", "2025-2026", "2026-2027"]

DUMP = Path(__file__).resolve().parent.parent / "Database" / "Mapa" / "data dump"

HREF_RE = re.compile(r'href="([^"]*?\.xls)"', re.IGNORECASE)
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; ETG-softs-research/1.0)"}


def safra_label(folder):
    """'2018-2019' -> '18/19', matching the UNICA master's year columns."""
    a, b = folder.split("-")
    return f"{a[2:]}/{b[2:]}"


def list_xls(session, safra):
    """Every .xls URL on a safra page, following gov.br's b_start pagination."""
    found, start = [], 0
    while True:
        url = f"{BASE}/{safra}" + (f"?b_start:int={start}" if start else "")
        r = session.get(url, headers=HEADERS, timeout=60)
        r.raise_for_status()
        page = [urljoin(url, h) for h in HREF_RE.findall(r.text)]
        new = [u for u in page if u not in found]
        if not new:
            break
        found.extend(new)
        start += 20
    return sorted(set(found))


def fetch_safra(session, safra):
    out_dir = DUMP / safra
    out_dir.mkdir(parents=True, exist_ok=True)
    urls = list_xls(session, safra)
    got = skipped = 0
    for u in urls:
        dest = out_dir / u.rsplit("/", 1)[-1]
        if dest.exists() and dest.stat().st_size > 0:
            skipped += 1
            continue
        r = session.get(u, headers=HEADERS, timeout=120)
        if r.status_code != 200 or not r.content:
            print(f"    WARN {r.status_code} {dest.name}")
            continue
        dest.write_bytes(r.content)
        got += 1
        time.sleep(0.4)  # be polite to gov.br
    print(f"  {safra}: {len(urls)} listed, {got} downloaded, {skipped} already had")
    return got


def main():
    only = sys.argv[1:] or SAFRAS
    session = requests.Session()
    total = 0
    print(f"Downloading into {DUMP}")
    for safra in only:
        try:
            total += fetch_safra(session, safra)
        except Exception as exc:
            print(f"  {safra}: FAILED - {type(exc).__name__}: {exc}")
    print(f"Done. {total} new file(s).")


if __name__ == "__main__":
    main()
