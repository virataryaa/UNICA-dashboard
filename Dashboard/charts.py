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
GOOD = "#0ca30c"
CRITICAL = "#d03b3b"
MUTED = "#898781"
GRID = "#2c2c2a"
INK = "#ffffff"
SURFACE = "#1a1a19"

BASE_LAYOUT = dict(
    paper_bgcolor=SURFACE,
    plot_bgcolor=SURFACE,
    font=dict(color=INK, family="system-ui, -apple-system, Segoe UI, sans-serif"),
    margin=dict(l=50, r=20, t=50, b=40),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                bgcolor="rgba(0,0,0,0)"),
    xaxis=dict(gridcolor=GRID, linecolor=GRID, tickfont=dict(color=MUTED)),
    yaxis=dict(gridcolor=GRID, linecolor=GRID, tickfont=dict(color=MUTED),
               tickformat=",.0f"),
)


def _recent_year_cols(year_cols, n=6):
    return year_cols[-n:]


def _cumulative(df_wide, year_cols):
    cum = df_wide[year_cols].cumsum(skipna=True)
    return cum


def monthly_comparison(df_wide, year_cols, title="Monthly Comparison"):
    periods = df_wide["Period"].tolist()
    shown_years = _recent_year_cols(year_cols, 6)
    palette_cycle = list(SERIES.values())
    fig = go.Figure()
    for i, yr in enumerate(shown_years):
        is_last = i == len(shown_years) - 1
        fig.add_trace(go.Scatter(
            x=periods, y=df_wide[yr],
            mode="lines+markers" if is_last else "lines",
            name=yr,
            line=dict(width=3 if is_last else 2,
                       color=palette_cycle[i % len(palette_cycle)]),
            marker=dict(size=7) if is_last else dict(size=0),
        ))
    fig.update_layout(title=title, **BASE_LAYOUT)
    return fig


def cumulative_forecast(df_wide, year_cols, title="Cumulative (to date)"):
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
            name=yr,
            line=dict(width=3 if is_last else 2,
                       color=palette_cycle[i % len(palette_cycle)]),
        ))
    fig.update_layout(title=title, **BASE_LAYOUT)
    return fig


def min_max_avg(df_wide, year_cols, title="Current vs Min / Max / Avg"):
    periods = df_wide["Period"].tolist()
    current_year = year_cols[-1]
    history_years = [y for y in year_cols[:-1]]
    hist = df_wide[history_years]
    lo = hist.min(axis=1, skipna=True)
    hi = hist.max(axis=1, skipna=True)
    avg = hist.mean(axis=1, skipna=True)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=periods, y=lo, name="Min", mode="lines",
                              line=dict(width=2, color=SERIES["orange"], dash="dot")))
    fig.add_trace(go.Scatter(x=periods, y=hi, name="Max", mode="lines",
                              line=dict(width=2, color=SERIES["green"])))
    fig.add_trace(go.Scatter(x=periods, y=avg, name="Average", mode="lines",
                              line=dict(width=2, color=MUTED, dash="dash")))
    fig.add_trace(go.Scatter(x=periods, y=df_wide[current_year], name=current_year,
                              mode="lines+markers",
                              line=dict(width=3, color=INK),
                              marker=dict(size=7, symbol="diamond")))
    fig.update_layout(title=title, **BASE_LAYOUT)
    return fig


def _current_period_index(df_wide, year_cols):
    current_year = year_cols[-1]
    valid = df_wide[df_wide[current_year].notna()]
    if valid.empty:
        return 0
    return valid.index.max()


def summary_table(df_wide, year_cols):
    idx = _current_period_index(df_wide, year_cols)
    period_label = df_wide.loc[idx, "Period"]
    cum = _cumulative(df_wide, year_cols)
    values = cum.loc[idx, year_cols]
    pct_change = values.pct_change() * 100

    rows = []
    for yr in year_cols:
        rows.append({
            "Year": yr,
            f"Upto {period_label}": values[yr],
            "% Change": pct_change[yr],
        })
    return pd.DataFrame(rows), period_label


def ytd_comparison(df_wide, year_cols, title="YTD Comparison"):
    table, period_label = summary_table(df_wide, year_cols)
    colors = [CRITICAL if v < 0 else GOOD if pd.notna(v) else MUTED for v in table["% Change"]]
    text = [f"{v:+.0f}%" if pd.notna(v) else "" for v in table["% Change"]]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=table["Year"], y=table.iloc[:, 1],
        marker_color=SERIES["blue"],
        text=text, textposition="outside",
        textfont=dict(color=colors),
        name=f"Upto {period_label}",
    ))
    layout = dict(BASE_LAYOUT)
    layout["yaxis"] = dict(gridcolor=GRID, linecolor=GRID, tickfont=dict(color=MUTED),
                            tickformat=",.0f")
    fig.update_layout(title=f"{title} (Upto {period_label})", showlegend=False, **layout)
    return fig
