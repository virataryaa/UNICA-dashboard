import os
from datetime import datetime

import streamlit as st
import pandas as pd

from data_loader import load_wide, year_columns, dataset_slice, dataset_registry, DATA_PATH
from charts import (monthly_comparison, cumulative_forecast,
                     min_max_avg, summary_table, ytd_comparison, overview_row,
                     cumulative_ratio_stats, remaining_periods, default_ytd_yoy,
                     project_ytd_method, project_proportions_method,
                     project_manual_per_period, project_manual_yearly)
from table_html import raw_table_html, summary_table_html, overview_table_html

st.set_page_config(page_title="UNICA: Brazil", layout="wide")

CSS = """
<style>
.stApp { background-color: #ffffff; }
.block-container { max-width: 1400px; padding-top: 3rem; }

.unica-header {
    background: linear-gradient(135deg, #1e3a5f 0%, #0f2138 100%);
    padding: 11px 24px;
    border-radius: 10px;
    box-shadow: 0 3px 10px rgba(15, 33, 56, 0.18);
    text-align: center;
}
.unica-header h1 {
    color: white;
    font-size: 17px;
    font-weight: 600;
    letter-spacing: -0.01em;
    margin: 0;
}
.unica-header-menu h1 {
    color: #1e3a5f;
    font-size: 28px;
    font-weight: 800;
    letter-spacing: 0.02em;
    text-align: center;
    margin: 0;
}

div[data-testid="stMetric"] { background-color: #f9f9f7; }

/* Default (menu list) buttons: minimalist cards */
div[data-testid="stButton"] { margin-bottom: 6px; }
.stButton>button {
    background-color: #f9f9f7;
    color: #0b0b0b;
    border: 1px solid #ececea;
    border-radius: 10px;
    width: 100%;
    padding: 11px 18px;
    text-align: left;
    font-size: 14px;
    font-weight: 500;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: 0 1px 2px rgba(11, 11, 11, 0.02);
    transition: transform 0.15s ease, box-shadow 0.15s ease,
                border-color 0.15s ease, background-color 0.15s ease;
}
.stButton>button::after {
    content: "→";
    color: #c3c2b7;
    font-weight: 400;
    margin-left: 12px;
    transition: transform 0.15s ease, color 0.15s ease;
}
.stButton>button:hover {
    background-color: #ffffff;
    border-color: #0f766e;
    color: #0f766e;
    transform: translateY(-1px);
    box-shadow: 0 6px 16px rgba(15, 118, 110, 0.12);
}
.stButton>button:hover::after {
    color: #0f766e;
    transform: translateX(2px);
}
.stButton>button:disabled {
    background-color: #fbfbfa;
    color: #c3c2b7;
    border-color: #f1f0ed;
    box-shadow: none;
}
.stButton>button:disabled::after { color: #e1e0d9; }

/* Dataset page header: no background block anymore — plain text title
   plus a small Back button, laid out with Streamlit's native column
   vertical-alignment. */
.st-key-dataset_header {
    padding: 6px 20px 18px;
}
.st-key-dataset_header h1 {
    color: #1e3a5f;
    font-size: 20px;
    font-weight: 700;
    letter-spacing: -0.01em;
    margin: 0;
    text-align: center;
}
.st-key-dataset_header button {
    background-color: #f2f5f8 !important;
    border: 1px solid #dbe3ea !important;
    border-radius: 999px !important;
    color: #1e3a5f !important;
    font-weight: 500;
    font-size: 13px;
    padding: 6px 14px !important;
    width: auto !important;
    min-width: 0 !important;
    display: inline-flex !important;
    white-space: nowrap;
    box-shadow: none !important;
    transform: none !important;
}
.st-key-dataset_header button:hover {
    background-color: #e6edf5 !important;
    border-color: #1e3a5f !important;
}
.st-key-dataset_header button::after { content: none !important; }

/* Small muted pill bars (Overview period pickers, projection method picker) */
div[class*="_period_wrap"] button, div[class*="_pillbar"] button {
    font-size: 12px !important;
    padding: 3px 12px !important;
    min-height: 0 !important;
    color: #898781 !important;
    border-color: #e1e0d9 !important;
    background-color: #fbfbfa !important;
}
div[class*="_period_wrap"] button p, div[class*="_pillbar"] button p {
    font-size: 12px !important;
    color: inherit !important;
}
div[class*="_period_wrap"] button[aria-pressed="true"],
div[class*="_period_wrap"] button[aria-checked="true"],
div[class*="_pillbar"] button[aria-pressed="true"],
div[class*="_pillbar"] button[aria-checked="true"] {
    color: #52514e !important;
    border-color: #c3c2b7 !important;
    background-color: #f2f1ee !important;
    font-weight: 600;
}

/* Scenario Projection card: compact, boxed, small inputs */
.st-key-sc_proj_card {
    border: 1px solid #e1e0d9;
    border-radius: 10px;
    padding: 12px 16px;
    margin-top: 8px;
    background-color: #fbfbfa;
}
.st-key-sc_proj_card [data-testid="stNumberInput"] label p {
    font-size: 11px !important;
    color: #898781 !important;
}
.st-key-sc_proj_card [data-testid="stNumberInput"] input {
    font-size: 12px !important;
    padding: 4px 8px !important;
    height: 30px !important;
}
.st-key-sc_proj_card [data-testid="stNumberInput"] button {
    height: 15px !important;
}
.st-key-sc_proj_card [data-testid="stCaptionContainer"] p {
    font-size: 11px !important;
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

if "page" not in st.session_state:
    st.session_state.page = "menu"

df_wide_all = load_wide()
registry = dataset_registry(df_wide_all)
kind_by_dataset = dict(zip(registry["Dataset"], registry["Kind"]))
available = set(registry["Dataset"])

UNITS = {
    "Sugarcane Crush": "MT",
    "Sugar": "MT",
    "Ethanol": "Litres",
    "ATR": "MT",
    "ATR Yield": "kg/ton",
    "Sugar Mix": "%",
    "Ethanol Sales": "Litres",
    "Hydrous (Int)": "Litres",
    "Anhydrous (Int)": "Litres",
    "Fuel Consumption": "Litres",
    "Gasolina Consumption": "Litres",
    "Hydrous Share": "%",
}


def _compute_fuel_consumption():
    hyd = dataset_slice(df_wide_all, "Hydrous (Int)")
    anh = dataset_slice(df_wide_all, "Anhydrous (Int)")
    if hyd.empty or anh.empty:
        return pd.DataFrame()
    year_cols = year_columns(hyd)
    out = hyd[["Period"]].copy()
    out.insert(0, "Kind", "flow")
    out.insert(0, "Dataset", "Fuel Consumption")
    for y in year_cols:
        out[y] = hyd[y] * 0.7 + anh[y] / 0.3
    return out


def _compute_gasolina_consumption():
    anh = dataset_slice(df_wide_all, "Anhydrous (Int)")
    if anh.empty:
        return pd.DataFrame()
    year_cols = year_columns(anh)
    out = anh[["Period"]].copy()
    out.insert(0, "Kind", "flow")
    out.insert(0, "Dataset", "Gasolina Consumption")
    for y in year_cols:
        out[y] = anh[y] / 0.27
    return out


def _compute_hydrous_share():
    hyd = dataset_slice(df_wide_all, "Hydrous (Int)")
    anh = dataset_slice(df_wide_all, "Anhydrous (Int)")
    if hyd.empty or anh.empty:
        return pd.DataFrame()
    year_cols = year_columns(hyd)
    out = hyd[["Period"]].copy()
    out.insert(0, "Kind", "ratio")
    out.insert(0, "Dataset", "Hydrous Share")
    for y in year_cols:
        fuel = hyd[y] * 0.7 + anh[y] / 0.3
        out[y] = hyd[y] * 0.7 / fuel * 100
    return out


# name -> (compute_fn, kind)
DERIVED = {
    "Fuel Consumption": (_compute_fuel_consumption, "flow"),
    "Gasolina Consumption": (_compute_gasolina_consumption, "flow"),
    "Hydrous Share": (_compute_hydrous_share, "ratio"),
}

BIWEEKLY_DATASETS = ["Sugarcane Crush", "Sugar", "Ethanol", "ATR", "ATR Yield", "Sugar Mix"]
MONTHLY_DATASETS = [
    "Ethanol Sales", "Hydrous (Int)", "Anhydrous (Int)",
    "Fuel Consumption", "Gasolina Consumption", "Hydrous Share",
]


def _load_dataset(name):
    if name in DERIVED:
        compute_fn, kind = DERIVED[name]
        return compute_fn(), kind
    df_wide = dataset_slice(df_wide_all, name)
    kind = kind_by_dataset.get(name, "flow")
    return df_wide, kind


def go_to(page):
    st.session_state.page = page


def _latest_period_label(name):
    df_wide, kind = _load_dataset(name)
    if df_wide.empty:
        return None
    year_cols = year_columns(df_wide)
    r = overview_row(df_wide, year_cols, kind)
    return f"{r['period']} {year_cols[-1]}"


def render_menu():
    left, center, right = st.columns([1, 2, 1])
    with center:
        st.markdown(
            '<div style="text-align:center;"><div class="unica-header-menu"><h1>UNICA</h1></div></div>',
            unsafe_allow_html=True,
        )

        updated_str = datetime.fromtimestamp(os.path.getmtime(DATA_PATH)).strftime("%d %b %Y, %H:%M")
        biweekly_latest = _latest_period_label(BIWEEKLY_DATASETS[0])
        monthly_latest = _latest_period_label(MONTHLY_DATASETS[0])
        st.markdown(
            f'<div style="text-align:center;color:#898781;font-size:12px;margin:10px 0 18px;">'
            f'Data last updated {updated_str} &nbsp;·&nbsp; '
            f'Bi-Weekly through {biweekly_latest} &nbsp;·&nbsp; '
            f'Monthly through {monthly_latest}</div>',
            unsafe_allow_html=True,
        )

        st.button("Overview", key="menu_Overview", on_click=go_to, args=("Overview",),
                   use_container_width=True)

        col_left, col_right = st.columns(2)
        with col_left:
            for item in BIWEEKLY_DATASETS:
                disabled = item not in available and item not in DERIVED
                label = item if not disabled else f"{item} (coming soon)"
                st.button(label, key=f"menu_{item}", disabled=disabled,
                           on_click=go_to, args=(item,), use_container_width=True)
        with col_right:
            for item in MONTHLY_DATASETS:
                disabled = item not in available and item not in DERIVED
                label = item if not disabled else f"{item} (coming soon)"
                st.button(label, key=f"menu_{item}", disabled=disabled,
                           on_click=go_to, args=(item,), use_container_width=True)


def render_overview():
    with st.container(key="dataset_header"):
        col_back, col_title, col_spacer = st.columns([1, 5, 1], vertical_alignment="center")
        with col_back:
            st.button("← Back", on_click=go_to, args=("menu",))
        with col_title:
            st.markdown("<h1>Overview</h1>", unsafe_allow_html=True)

    def _available_periods(names):
        """Periods (in order) where the current year already has a
        reading, for the group's representative dataset. All datasets in
        a granularity group share identical row positions per period, so
        one representative dataset's row index applies to every dataset
        in the group."""
        df_wide, kind = _load_dataset(names[0])
        if df_wide.empty:
            return [], {}
        year_cols = year_columns(df_wide)
        current_year = year_cols[-1]
        mask = df_wide[current_year].notna()
        sub = df_wide.loc[mask, "Period"]
        return sub.tolist(), dict(zip(sub.tolist(), sub.index.tolist()))

    # For these ratios, "cumulative" is properly derived from the underlying
    # flow components (cumulative numerator / cumulative denominator)
    # instead of naively averaging the reported ratio period-to-period.
    CUMULATIVE_RATIO_OVERRIDES = {
        "ATR Yield": dict(numerator="ATR", denominator="Sugarcane Crush", scale=1000.0, denom_multiplier=1.0),
        "Sugar Mix": dict(numerator="Sugar", denominator="ATR", scale=100.0, denom_multiplier=0.953),
    }

    def _build_rows(names, period_idx):
        standalone_rows, cumulative_rows = [], []
        year_cols_ref = None
        for name in names:
            df_wide, kind = _load_dataset(name)
            if df_wide.empty:
                continue
            year_cols = year_columns(df_wide)
            year_cols_ref = year_cols
            r = overview_row(df_wide, year_cols, kind, idx=period_idx)
            unit = UNITS.get(name, "")
            standalone_rows.append({**r["standalone"], "name": name, "unit": unit, "period": r["period"]})

            if name in CUMULATIVE_RATIO_OVERRIDES:
                spec = CUMULATIVE_RATIO_OVERRIDES[name]
                num_df, _ = _load_dataset(spec["numerator"])
                den_df, _ = _load_dataset(spec["denominator"])
                cum_stats = cumulative_ratio_stats(
                    num_df, den_df, year_cols, period_idx,
                    scale=spec["scale"], denom_multiplier=spec["denom_multiplier"],
                )
                cumulative_rows.append({**cum_stats, "name": name, "unit": unit, "period": r["period"]})
            else:
                cumulative_rows.append({**r["cumulative"], "name": name, "unit": unit, "period": r["period"]})
        return standalone_rows, cumulative_rows, year_cols_ref

    def _render_group(group_label, names, widget_key):
        periods, label_to_idx = _available_periods(names)
        if not periods:
            return
        with st.container(key=f"{widget_key}_wrap"):
            selected = st.pills(
                f"{group_label} period", options=periods, default=periods[-1],
                selection_mode="single", key=widget_key,
            )
        if selected is None:
            selected = periods[-1]
        period_idx = label_to_idx[selected]

        standalone_rows, cumulative_rows, year_cols_ref = _build_rows(names, period_idx)
        if not year_cols_ref:
            return
        prev_year, current_year = year_cols_ref[-2], year_cols_ref[-1]
        left, right = st.columns(2)
        with left:
            st.markdown(
                overview_table_html(standalone_rows, f"{group_label} Comparison",
                                     prev_year, current_year),
                unsafe_allow_html=True,
            )
        with right:
            st.markdown(
                overview_table_html(cumulative_rows, "Cumulative Comparison",
                                     prev_year, current_year),
                unsafe_allow_html=True,
            )

    _render_group("Bi-Weekly", BIWEEKLY_DATASETS, "overview_biweekly_period")
    _render_group("Monthly", MONTHLY_DATASETS, "overview_monthly_period")


def _render_projection_ui(df_wide, year_cols, unit):
    """Scenario Projection block: lets the user forecast the remaining
    periods of the current season using one of four methods, returning a
    {period_label: projected_value} dict for the charts to extend with.
    Rendered compact, meant to sit below the charts it feeds."""
    rem = remaining_periods(df_wide, year_cols)
    if not rem:
        return None

    current_year = year_cols[-1]
    with st.container(key="sc_proj_card"):
        st.markdown(
            f'<div style="font-size:0.85rem;font-weight:600;color:#1e3a5f;margin:0 0 6px;">'
            f'Scenario Projection <span style="font-weight:400;color:#898781;font-size:0.8rem;">'
            f'&nbsp;remaining periods of {current_year} ({rem[0]} – {rem[-1]})</span></div>',
            unsafe_allow_html=True,
        )
        with st.container(key="sc_proj_method_pillbar"):
            method = st.pills(
                "Method", ["YTD Method", "Proportions", "Manual (per Period)", "Manual (Yearly)"],
                default="YTD Method", selection_mode="single",
                key="sc_proj_method", label_visibility="collapsed",
            )
        if method is None:
            method = "YTD Method"

        pc1, pc2 = st.columns([1, 2])
        if method == "YTD Method":
            with pc1:
                default_yoy = default_ytd_yoy(df_wide, year_cols)
                yoy_pct = st.number_input(
                    "YoY % vs previous year", value=float(default_yoy), step=0.5,
                    format="%.1f", key="sc_proj_yoy",
                )
            proj_vals = project_ytd_method(df_wide, year_cols, yoy_pct)

        elif method == "Proportions":
            proj_vals, implied_total = project_proportions_method(df_wide, year_cols)
            if implied_total:
                with pc1:
                    st.caption(f"Implied full-season total: {implied_total:,.0f} {unit}")
            else:
                st.caption("No complete historical years available for this method.")

        elif method == "Manual (per Period)":
            with pc1:
                manual_val = st.number_input(
                    f"Value per remaining period ({unit})",
                    min_value=0.0, value=0.0, step=100000.0, key="sc_proj_manual",
                )
            proj_vals = project_manual_per_period(df_wide, year_cols, manual_val)

        else:  # Manual (Yearly)
            cy_ytd = df_wide[current_year].sum(skipna=True)
            with pc1:
                target = st.number_input(
                    f"Full season target ({unit})",
                    min_value=0.0, value=float(cy_ytd), step=1000000.0, format="%.0f",
                    key="sc_proj_yearly",
                )
            proj_vals, remaining_budget = project_manual_yearly(df_wide, year_cols, target)
            with pc1:
                st.caption(f"YTD actual: {cy_ytd:,.0f}  ·  Remaining budget: {remaining_budget:,.0f}")

    return proj_vals


def render_dataset(name):
    with st.container(key="dataset_header"):
        col_back, col_title, col_spacer = st.columns([1, 5, 1], vertical_alignment="center")
        with col_back:
            st.button("← Back", on_click=go_to, args=("menu",))
        with col_title:
            st.markdown(f"<h1>{name}</h1>", unsafe_allow_html=True)

    df_wide, kind = _load_dataset(name)

    if df_wide.empty:
        st.info("No data loaded for this dataset yet.")
        return
    year_cols = year_columns(df_wide)
    unit = UNITS.get(name, "")

    proj_vals = None
    if name == "Sugarcane Crush":
        proj_vals = _render_projection_ui(df_wide, year_cols, unit)

    PANEL_H = 330
    if kind == "ratio":
        cols = st.columns([1, 1])
        with cols[0]:
            st.plotly_chart(monthly_comparison(df_wide, year_cols, height=PANEL_H), use_container_width=True)
        with cols[1]:
            st.plotly_chart(min_max_avg(df_wide, year_cols, height=PANEL_H), use_container_width=True)
    else:
        cols = st.columns([1, 1])
        with cols[0]:
            st.plotly_chart(monthly_comparison(df_wide, year_cols, height=PANEL_H, proj_vals=proj_vals), use_container_width=True)
            st.plotly_chart(min_max_avg(df_wide, year_cols, height=PANEL_H, proj_vals=proj_vals), use_container_width=True)
        with cols[1]:
            st.plotly_chart(
                cumulative_forecast(df_wide, year_cols, height=2 * PANEL_H + 40, proj_vals=proj_vals),
                use_container_width=True,
            )

    bottom_cols = st.columns([1, 3])
    with bottom_cols[0]:
        table, period_label = summary_table(df_wide, year_cols, kind)
        st.markdown(summary_table_html(table, period_label, unit), unsafe_allow_html=True)
    with bottom_cols[1]:
        st.plotly_chart(ytd_comparison(df_wide, year_cols, kind=kind, height=PANEL_H),
                         use_container_width=True)

    st.markdown(
        raw_table_html(df_wide, year_cols, title=name, unit=unit, kind=kind),
        unsafe_allow_html=True,
    )


if st.session_state.page == "menu":
    render_menu()
elif st.session_state.page == "Overview":
    render_overview()
else:
    render_dataset(st.session_state.page)
