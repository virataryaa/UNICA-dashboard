import pandas as pd

from charts import GOOD, CRITICAL, GRID, INK, MUTED

LIGHT_GREEN = (234, 250, 240)
DARK_GREEN = (10, 110, 66)


def _green_shade(t):
    t = max(0.0, min(1.0, t))
    r = LIGHT_GREEN[0] + (DARK_GREEN[0] - LIGHT_GREEN[0]) * t
    g = LIGHT_GREEN[1] + (DARK_GREEN[1] - LIGHT_GREEN[1]) * t
    b = LIGHT_GREEN[2] + (DARK_GREEN[2] - LIGHT_GREEN[2]) * t
    text = "#ffffff" if t > 0.55 else "#0b0b0b"
    return f"rgb({int(r)},{int(g)},{int(b)})", text


def _bar_cell(pct, scale=50):
    if pd.isna(pct):
        return ""
    color = CRITICAL if pct < 0 else GOOD
    width = max(4, min(abs(pct) / scale * 100, 100))
    return (
        '<div style="position:relative;height:16px;background:#f2f1ee;'
        'border-radius:3px;overflow:hidden;">'
        f'<div style="position:absolute;top:0;left:0;height:100%;width:{width:.0f}%;'
        f'background:{color};opacity:0.28;"></div>'
        f'<div style="position:relative;z-index:1;text-align:center;font-size:10px;'
        f'line-height:16px;font-weight:600;color:{color};">{pct:+.2f}%</div>'
        '</div>'
    )


def raw_table_html(df_wide, year_cols, title, unit=""):
    body = df_wide[year_cols]
    vmin = body.min(numeric_only=True).min()
    vmax = body.max(numeric_only=True).max()
    span = (vmax - vmin) or 1

    current_year, prev_year = year_cols[-1], year_cols[-2]
    yoy = (df_wide[current_year] - df_wide[prev_year]) / df_wide[prev_year] * 100
    hist_avg = df_wide[year_cols[:-1]].mean(axis=1, skipna=True)
    chg_avg = (df_wide[current_year] - hist_avg) / hist_avg * 100

    heading = f"{title} (in {unit})" if unit else title

    header_cells = "".join(f"<th>{y}</th>" for y in year_cols)
    rows_html = []
    for _, row in df_wide.iterrows():
        cells = [f'<td class="period-col">{row["Period"]}</td>']
        for y in year_cols:
            v = row[y]
            if pd.isna(v):
                cells.append('<td></td>')
                continue
            t = (v - vmin) / span
            bg, txt = _green_shade(t)
            cells.append(
                f'<td style="background:{bg};color:{txt};">{v:,.0f}</td>'
            )
        idx = row.name
        cells.append(f'<td class="bar-cell">{_bar_cell(yoy.loc[idx])}</td>')
        cells.append(f'<td class="bar-cell">{_bar_cell(chg_avg.loc[idx])}</td>')
        rows_html.append("<tr>" + "".join(cells) + "</tr>")

    totals = []
    for y in year_cols:
        col = df_wide[y]
        is_current_year = y == current_year
        totals.append(None if (is_current_year and col.isna().any()) else col.sum(skipna=True))
    total_cells = '<td class="period-col">Total</td>' + "".join(
        f'<td>{v:,.0f}</td>' if v is not None else '<td></td>' for v in totals
    ) + '<td></td><td></td>'

    html = f"""
    <div class="unica-table-wrap">
    <style>
    .unica-table-wrap {{ overflow-x: auto; margin: 16px 0; border: 1px solid {GRID}; border-radius: 6px;
                          max-height: 480px; overflow-y: auto; }}
    .unica-table {{ border-collapse: collapse; width: 100%; font-size: 11px;
                    font-family: system-ui, -apple-system, Segoe UI, sans-serif; }}
    .unica-table caption {{ text-align: left; font-weight: 700; font-size: 13px;
                             padding: 6px 10px; color: {INK}; }}
    .unica-table th {{ background: #0f766e; color: white; padding: 4px 8px;
                        text-align: right; position: sticky; top: 0; white-space: nowrap; }}
    .unica-table th.period-col, .unica-table td.period-col {{ text-align: left; font-style: italic;
                        color: {MUTED}; white-space: nowrap; }}
    .unica-table td {{ padding: 3px 8px; text-align: right; white-space: nowrap; }}
    .unica-table td.bar-cell {{ min-width: 70px; padding: 2px 6px; }}
    .unica-table tr.total-row td {{ font-weight: 700; border-top: 2px solid {INK}; }}
    </style>
    <table class="unica-table">
      <caption>{heading}</caption>
      <thead><tr><th class="period-col">Upto</th>{header_cells}<th>YoY</th><th>Chg w.r.t Avg</th></tr></thead>
      <tbody>
        {''.join(rows_html)}
        <tr class="total-row">{total_cells}</tr>
      </tbody>
    </table>
    </div>
    """
    return html
