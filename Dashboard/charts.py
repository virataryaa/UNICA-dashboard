import numpy as np
import pandas as pd
import plotly.graph_objects as go

# Validated categorical slots (dark-mode steps) from the dataviz reference palette.
SERIES = {
    "blue": "#3987e5",
    "green": "#008300",
    "magenta": "#d55181",
    "yellow": "#c98500",
    "aqua": "#199e70",
    "orange": "#d95926",
    "violet": "#9085e9",
    "red": "#e66767",
}
GOOD = "#006300"
CRITICAL = "#d03b3b"
MUTED = "#898781"
GRID = "#e1e0d9"
INK = "#0b0b0b"
SURFACE = "#fcfcfb"
NAVY_SOFT = "#3d5d85"


def _layout(title, height=None):
    layout = dict(
        title=dict(text=title, x=0.01, xanchor="left", y=0.97, yanchor="top",
                   font=dict(size=15)),
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        font=dict(color=INK, family="system-ui, -apple-system, Segoe UI, sans-serif"),
        margin=dict(l=50, r=20, t=50, b=100),
        legend=dict(orientation="h", yanchor="top", y=-0.3, xanchor="left", x=0,
                    bgcolor="rgba(0,0,0,0)"),
        xaxis=dict(gridcolor=GRID, linecolor=GRID, tickfont=dict(color=MUTED)),
        yaxis=dict(gridcolor=GRID, linecolor=GRID, tickfont=dict(color=MUTED),
                   tickformat=",.0f"),
    )
    if height:
        layout["height"] = height
    return layout


def _recent_year_cols(year_cols, n=6):
    return year_cols[-n:]


def _cumulative(df_wide, year_cols):
    cum = df_wide[year_cols].cumsum(skipna=True)
    return cum


def monthly_comparison(df_wide, year_cols, title="Monthly Comparison", height=None):
    periods = df_wide["Period"].tolist()
    shown_years = _recent_year_cols(year_cols, 6)
    palette_cycle = list(SERIES.values())
    fig = go.Figure()
    for i, yr in enumerate(shown_years):
        is_last = i == len(shown_years) - 1
        fig.add_trace(go.Scatter(
            x=periods, y=df_wide[yr],
            mode="lines+markers" if is_last else "lines",
            name=yr, connectgaps=True,
            line=dict(width=4 if is_last else 2,
                       color=INK if is_last else palette_cycle[i % len(palette_cycle)]),
            marker=dict(size=7, color=INK) if is_last else dict(size=0),
        ))
    fig.update_layout(**_layout(title, height))
    return fig


def cumulative_forecast(df_wide, year_cols, title="Cumulative (to date)", height=None):
    periods = df_wide["Period"].tolist()
    cum = _cumulative(df_wide, year_cols)
    shown_years = _recent_year_cols(year_cols, 7)
    palette_cycle = list(SERIES.values())
    fig = go.Figure()
    for i, yr in enumerate(shown_years):
        is_last = i == len(shown_years) - 1
        fig.add_trace(go.Scatter(
            x=periods, y=cum[yr],
            mode="lines",
            name=yr, connectgaps=True,
            line=dict(width=4 if is_last else 2,
                       color=INK if is_last else palette_cycle[i % len(palette_cycle)]),
        ))
    fig.update_layout(**_layout(title, height))
    return fig


def min_max_avg(df_wide, year_cols, title="Current vs Min / Max / Avg", height=None):
    periods = df_wide["Period"].tolist()
    current_year = year_cols[-1]
    history_years = [y for y in year_cols[:-1]]
    hist = df_wide[history_years]
    lo = hist.min(axis=1, skipna=True)
    hi = hist.max(axis=1, skipna=True)
    avg = hist.mean(axis=1, skipna=True)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=periods, y=lo, name="Min", mode="lines", connectgaps=True,
                              line=dict(width=2, color=SERIES["orange"], dash="dot")))
    fig.add_trace(go.Scatter(x=periods, y=hi, name="Max", mode="lines", connectgaps=True,
                              line=dict(width=2, color=SERIES["green"], dash="dot")))
    fig.add_trace(go.Scatter(x=periods, y=avg, name="Average", mode="lines", connectgaps=True,
                              line=dict(width=2, color=MUTED, dash="dash")))
    fig.add_trace(go.Scatter(x=periods, y=df_wide[current_year], name=current_year,
                              mode="lines+markers", connectgaps=True,
                              line=dict(width=3, color=INK),
                              marker=dict(size=7, symbol="diamond")))
    fig.update_layout(**_layout(title, height))
    return fig


def _current_period_index(df_wide, year_cols):
    current_year = year_cols[-1]
    valid = df_wide[df_wide[current_year].notna()]
    if valid.empty:
        return 0
    return valid.index.max()


def summary_table(df_wide, year_cols, kind="flow"):
    idx = _current_period_index(df_wide, year_cols)
    period_label = df_wide.loc[idx, "Period"]
    if kind == "ratio":
        values = df_wide.loc[idx, year_cols]
        col_label = str(period_label)
    else:
        cum = _cumulative(df_wide, year_cols)
        values = cum.loc[idx, year_cols]
        col_label = f"Upto {period_label}"
    pct_change = values.pct_change(fill_method=None) * 100

    rows = []
    for yr in year_cols:
        rows.append({
            "Year": yr,
            col_label: values[yr],
            "% Change": pct_change[yr],
        })
    return pd.DataFrame(rows), period_label


def _pack_stats(series, current_year, prev_year, hist_years):
    latest = series[current_year]
    prev = series[prev_year]
    avg = series[hist_years].mean(skipna=True)
    yoy = (latest - prev) / prev * 100 if prev not in (0, None) and pd.notna(prev) else None
    vs_avg = (latest - avg) / avg * 100 if avg not in (0, None) and pd.notna(avg) else None
    return dict(latest=latest, prev=prev, yoy=yoy, vs_avg=vs_avg)


def overview_row(df_wide, year_cols, kind="flow", idx=None):
    """Returns both a standalone (single period reading) and a
    cumulative-to-date reading. For flow metrics, cumulative is a running
    sum. For ratio metrics — which have no meaningful sum — cumulative is
    the season-to-date average of the ratio (we don't store the underlying
    numerator/denominator needed for a true cumulative ratio).

    idx: explicit row position to read (e.g. a period the user picked via
    a slicer). Defaults to the latest period with current-year data."""
    if idx is None:
        idx = _current_period_index(df_wide, year_cols)
    period_label = df_wide.loc[idx, "Period"]
    current_year, prev_year = year_cols[-1], year_cols[-2]
    hist_years = year_cols[:-1]

    standalone = df_wide.loc[idx, year_cols]
    if kind == "flow":
        cum = _cumulative(df_wide, year_cols)
        cumulative = cum.loc[idx, year_cols]
    else:
        cumulative = df_wide.loc[:idx, year_cols].mean(skipna=True)

    return dict(
        period=period_label,
        standalone=_pack_stats(standalone, current_year, prev_year, hist_years),
        cumulative=_pack_stats(cumulative, current_year, prev_year, hist_years),
    )


def ytd_comparison(df_wide, year_cols, kind="flow", title=None, height=None):
    table, period_label = summary_table(df_wide, year_cols, kind)
    value_col = table.columns[1]
    colors = [CRITICAL if v < 0 else GOOD if pd.notna(v) else MUTED for v in table["% Change"]]
    text = [f"{v:+.0f}%" if pd.notna(v) else "" for v in table["% Change"]]

    n = len(table)
    bar_colors = [NAVY_SOFT] * (n - 1) + [INK] if n else []

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=table["Year"], y=table[value_col],
        marker=dict(color=bar_colors, line=dict(color=SURFACE, width=1.5)),
        text=text, textposition="outside",
        textfont=dict(color=colors),
        name=value_col,
    ))
    base_title = title or ("YTD Comparison" if kind == "flow" else "Period Comparison")
    layout = _layout(f"{base_title} ({value_col})", height)
    fig.update_layout(showlegend=False, **layout)
    return fig
