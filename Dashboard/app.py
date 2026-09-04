import os
from datetime import datetime

import streamlit as st
import pandas as pd

from data_loader import (load_wide, year_columns, dataset_slice, dataset_registry, DATA_PATH,
                          load_mapa, mapa_slice, mapa_states, mapa_year_columns,
                          MAPA_GROUPS, MAPA_REGIONS, MAPA_PATH,
                          SOURCE_PAIRS, source_compare_frame)
from charts import (monthly_comparison, cumulative_forecast,
                     min_max_avg, summary_table, ytd_comparison, overview_row,
                     cumulative_ratio_stats, remaining_periods, default_ytd_yoy,
                     project_ytd_method, project_proportions_method,
                     project_manual_per_period, project_manual_yearly,
                     source_compare_line, source_compare_scatter, source_stats)
from table_html import (raw_table_html, summary_table_html, overview_table_html,
                         recon_table_html, source_stats_table_html)

st.set_page_config(page_title="UNICA: Brazil", layout="wide",
                    initial_sidebar_state="expanded")

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

/* MAPA is a different source, not another UNICA series, so its entry point
   sits apart at the foot of the menu and wears the accent tint rather than
   the neutral the series buttons share. */
.st-key-mapa_entry { margin-top: 26px; }
.st-key-mapa_entry .stButton>button {
    background-color: #eef6f4;
    border-color: #d3e7e2;
    color: #0f766e;
}
.st-key-mapa_entry .stButton>button::after { color: #7fb3ab; }
.st-key-mapa_entry .stButton>button:hover {
    background-color: #e4f1ee;
    border-color: #0f766e;
    color: #0b5c55;
}
.st-key-mapa_entry .stButton>button:hover::after { color: #0f766e; }

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
    st.session_state.page = "home"

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


def render_home():
    left, center, right = st.columns([1, 2, 1])
    with center:
        st.markdown(
            '<div style="text-align:center;"><div class="unica-header-menu">'
            '<h1>Brazil</h1></div></div>',
            unsafe_allow_html=True,
        )
        unica_at = datetime.fromtimestamp(os.path.getmtime(DATA_PATH)).strftime("%d %b %Y")
        mapa_at = datetime.fromtimestamp(os.path.getmtime(MAPA_PATH)).strftime("%d %b %Y")
        st.markdown(
            f'<div style="text-align:center;color:#898781;font-size:12px;'
            f'margin:10px 0 18px;">UNICA updated {unica_at} &nbsp;·&nbsp; '
            f'MAPA updated {mapa_at}</div>',
            unsafe_allow_html=True,
        )

        st.button("UNICA", key="home_unica", on_click=go_to, args=("menu",),
                   use_container_width=True)
        with st.container(key="mapa_entry"):
            st.button("MAPA", key="home_mapa", on_click=go_to, args=("mapa_menu",),
                       use_container_width=True)
            st.button("MAPA vs UNICA", key="home_recon", on_click=go_to,
                       args=("mapa_recon",), use_container_width=True)


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

        st.button("← Back", key="menu_back", on_click=go_to, args=("home",))

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

        pc1, pc2, pc3 = st.columns([1, 1, 3])
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

    _render_panels(df_wide, year_cols, kind, name, unit, proj_vals)


def _render_panels(df_wide, year_cols, kind, title, unit, proj_vals=None):
    """The chart + table body shared by every series page. Ratios and stocks
    are levels rather than quantities, so they skip the cumulative panel and
    the running-sum tables that only mean something for a flow."""
    PANEL_H = 330
    if kind in ("ratio", "stock"):
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
        raw_table_html(df_wide, year_cols, title=title, unit=unit, kind=kind),
        unsafe_allow_html=True,
    )


# --- MAPA / SAPCANA ------------------------------------------------------
# MAPA covers every mill in Brazil, not just UNICA's Centro-Sul membership,
# and publishes ethanol stocks and movements that UNICA does not report at
# all. It also lands roughly a fortnight ahead of UNICA.

MAPA_LABELS = {
    "Cana": "Cane Crush",
    "Acucar": "Sugar",
    "Etanol Total": "Ethanol Total",
    "Producao": "Production",
    "Entradas": "Inflows",
    "Saidas Distrib": "Sales to Distributors",
    "Saidas M.Ext": "Exports",
    "Saidas Outras": "Other Outflows",
    "Estoque E.Fisico": "Stock (Physical)",
    "Estoque E.Disp": "Stock (Available)",
}

MAPA_TONNE_DATASETS = {"Cana", "Acucar"}


def mapa_label(dataset):
    """Short label for a series, with the grade prefix stripped - the group
    heading already says whether it is anhydrous or hydrous."""
    for prefix in ("Anidro ", "Hidratado "):
        if dataset.startswith(prefix):
            return MAPA_LABELS.get(dataset[len(prefix):], dataset[len(prefix):])
    return MAPA_LABELS.get(dataset, dataset)


def mapa_unit(dataset):
    return "MT" if dataset in MAPA_TONNE_DATASETS else "m3"


def mapa_region_name(level, region):
    for name, lvl, code in MAPA_REGIONS:
        if (lvl, code) == (level, region):
            return name
    return region


def go_to_mapa(dataset):
    st.session_state.page = "mapa:" + dataset


def _mapa_selected_region():
    return st.session_state.get("mapa_region", ("country", "BR"))


_MAPA_GROUP_HEAD = ('<div style="color:#1e3a5f;font-size:13px;font-weight:600;'
                    'margin:14px 0 6px;">{label}</div>')


def render_mapa_menu():
    mapa = load_mapa()
    left, center, right = st.columns([1, 2, 1])
    with center:
        st.markdown(
            '<div style="text-align:center;"><div class="unica-header-menu"><h1>MAPA</h1></div></div>',
            unsafe_allow_html=True,
        )
        updated = datetime.fromtimestamp(os.path.getmtime(MAPA_PATH)).strftime("%d %b %Y, %H:%M")
        st.markdown(
            f'<div style="text-align:center;color:#898781;font-size:12px;margin:10px 0 18px;">'
            f'Data last updated {updated}</div>',
            unsafe_allow_html=True,
        )

        st.button("← Back", key="mapa_back", on_click=go_to, args=("home",))

        def _group(name):
            for ds in MAPA_GROUPS[name]:
                st.button(mapa_label(ds), key=f"mapa_menu_{ds}",
                           on_click=go_to_mapa, args=(ds,), use_container_width=True)

        # Headed "Totals", not "Production": each grade column below opens with
        # its own Production button, and two different things under one word
        # on one screen is a coin toss for the reader.
        st.markdown(_MAPA_GROUP_HEAD.format(label="Totals"), unsafe_allow_html=True)
        _group("Production")

        # Anhydrous and hydrous carry the same seven series each, so the two
        # columns line up row for row - production against production, stock
        # against stock - and the grades read as a pair rather than as one
        # list after another.
        col_left, col_right = st.columns(2)
        with col_left:
            st.markdown(_MAPA_GROUP_HEAD.format(label="Anhydrous"), unsafe_allow_html=True)
            _group("Anhydrous")
        with col_right:
            st.markdown(_MAPA_GROUP_HEAD.format(label="Hydrous"), unsafe_allow_html=True)
            _group("Hydrous")


def render_mapa_dataset(dataset):
    level, region = _mapa_selected_region()
    region_name = mapa_region_name(level, region)
    title = f"{mapa_label(dataset)} — {region_name}"

    with st.container(key="dataset_header"):
        col_back, col_title, col_spacer = st.columns([1, 5, 1], vertical_alignment="center")
        with col_back:
            st.button("← Back", on_click=go_to, args=("mapa_menu",))
        with col_title:
            st.markdown(f"<h1>{title}</h1>", unsafe_allow_html=True)

    df_wide, kind = mapa_slice(load_mapa(), level, region, dataset)
    if df_wide.empty:
        st.info(f"MAPA reports no {mapa_label(dataset)} for {region_name}.")
        return

    year_cols = year_columns(df_wide)
    _render_panels(df_wide, year_cols, kind, title, mapa_unit(dataset))


SOURCE_LABELS = {"Sugarcane Crush": "Cane crush", "Sugar": "Sugar",
                 "Ethanol": "Ethanol (total)"}


@st.cache_data(show_spinner=False)
def _source_frames():
    unica, mapa = load_wide(), load_mapa()
    return {u: source_compare_frame(unica, mapa, u, m) for u, m, _ in SOURCE_PAIRS}


def _render_source_comparison():
    """UNICA against MAPA Centro-Sul across the whole record, over whatever
    stretch the range control is set to.

    Anhydrous and hydrous are left out on purpose: UNICA publishes those two
    monthly against MAPA's fortnights, so they cannot share this axis without
    resampling one side into the other."""
    frames = _source_frames()
    dates = sorted({d for f in frames.values() for d in f["date"]})
    if len(dates) < 2:
        st.info("No overlapping periods between the two sources.")
        return
    dmin, dmax = dates[0], dates[-1]
    safras = sorted({s for f in frames.values() for s in f["safra"]},
                    key=lambda s: int(s[:2]))

    # Clamped every run, not just on first use: the range outlives the data it
    # was picked against, so an ingest that extends or trims the record would
    # otherwise leave a stored range outside the axis, which both widgets
    # below reject outright.
    stored = st.session_state.get("recon_slider")
    if not isinstance(stored, (tuple, list)) or len(stored) != 2:
        stored = (dmin, dmax)
    lo = min(max(stored[0], dmin), dmax)
    hi = min(max(stored[1], dmin), dmax)
    if hi < lo:
        lo, hi = dmin, dmax
    # Written back unconditionally, and always as a pair. st.slider decides
    # between a single handle and a range from the type of the value it starts
    # with, so leaving the key unset on a first visit hands back a scalar and
    # the unpack below fails.
    st.session_state.recon_slider = (lo, hi)

    # The season pills only jump the slider, and only on the run where the
    # selection actually changes. Applying them every run would drag the range
    # back to the season boundary each time the slider moved.
    picked = st.pills("Season", options=["All"] + safras, default=None,
                      selection_mode="single", label_visibility="collapsed",
                      key="recon_pill")

    if picked != st.session_state.get("recon_pill_applied"):
        st.session_state.recon_pill_applied = picked
        jump = None
        if picked == "All":
            jump = (dmin, dmax)
        elif picked:
            got = [d for f in frames.values()
                   for d, s in zip(f["date"], f["safra"]) if s == picked]
            if got:
                jump = (min(got), max(got))
        if jump and jump != (lo, hi):
            st.session_state.recon_slider = jump
            st.rerun()

    lo, hi = st.slider("Range", min_value=dmin, max_value=dmax,
                       key="recon_slider", format="MMM YYYY",
                       label_visibility="collapsed")

    lo_ts, hi_ts = pd.Timestamp(lo), pd.Timestamp(hi)
    selected, stat_rows = {}, []
    for unica_name, _mapa_name, unit in SOURCE_PAIRS:
        f = frames[unica_name]
        when = pd.to_datetime(f["date"])
        sel = f[(when >= lo_ts) & (when <= hi_ts)]
        selected[unica_name] = sel
        stat_rows.append({"label": SOURCE_LABELS[unica_name], "unit": unit,
                          "stats": source_stats(sel)})

    for unica_name, _mapa_name, unit in SOURCE_PAIRS:
        st.plotly_chart(
            source_compare_line(selected[unica_name], SOURCE_LABELS[unica_name], unit),
            use_container_width=True, key=f"recon_line_{unica_name}")

    st.markdown(
        '<div style="color:#898781;font-size:12px;margin:10px 0 2px;">'
        'MAPA on the horizontal, UNICA on the vertical, one dot per paired '
        'fortnight. The dashed line is parity; the solid line is the fit.</div>',
        unsafe_allow_html=True,
    )
    for col, (unica_name, _mapa_name, unit) in zip(st.columns(len(SOURCE_PAIRS)), SOURCE_PAIRS):
        with col:
            st.plotly_chart(
                source_compare_scatter(selected[unica_name], SOURCE_LABELS[unica_name], unit),
                use_container_width=True, key=f"recon_scatter_{unica_name}")

    st.markdown(source_stats_table_html(stat_rows), unsafe_allow_html=True)


def render_mapa_recon():
    with st.container(key="dataset_header"):
        col_back, col_title, col_spacer = st.columns([1, 5, 1], vertical_alignment="center")
        with col_back:
            st.button("← Back", on_click=go_to, args=("home",))
        with col_title:
            st.markdown("<h1>MAPA vs UNICA</h1>", unsafe_allow_html=True)

    _render_source_comparison()

    st.markdown(
        '<h2 style="font-size:16px;margin:26px 0 4px;">Cane, season by season</h2>',
        unsafe_allow_html=True,
    )

    unica, _ = _load_dataset("Sugarcane Crush")
    mapa, _ = mapa_slice(load_mapa(), "region", "CS", "Cana")
    years = [y for y in year_columns(unica) if y in mapa_year_columns(mapa)]
    if not years:
        st.info("No overlapping seasons between the two sources.")
        return

    u = unica.set_index("Period")
    m = mapa.set_index("Period")
    shared = [p for p in u.index if p in m.index]

    rows = []
    for y in years:
        both = [p for p in shared if pd.notna(u.loc[p, y]) and pd.notna(m.loc[p, y])]
        if not both:
            continue
        # When MAPA skips a publication, the next report's flow covers both
        # fortnights. The season total stays right, but a fortnight-matched
        # comparison then reads one MAPA period against two of UNICA's, so
        # those seasons are called out rather than silently compared.
        skipped = [p for p in shared
                   if pd.notna(u.loc[p, y]) and pd.isna(m.loc[p, y])]
        us, ms = u.loc[both, y].sum(), m.loc[both, y].sum()
        rows.append({
            "season": y,
            "fortnights": len(both),
            "unica": us,
            "mapa": ms,
            "gap": ms - us,
            "gap_pct": (ms - us) / us * 100 if us else None,
            "note": "MAPA has no print for " + ", ".join(skipped) if skipped else "",
        })

    st.markdown(recon_table_html(rows, unit="MT"), unsafe_allow_html=True)

    if any(r["note"] for r in rows):
        st.markdown(
            '<div style="color:#898781;font-size:12px;margin-top:8px;">'
            'Where a fortnight is missing on one side the two columns are not '
            'counting the same stretch of season, so the gap for that row '
            'overstates the real difference.</div>',
            unsafe_allow_html=True,
        )

    latest = years[-1]
    ahead = [p for p in m.index
             if pd.notna(m.loc[p, latest]) and pd.isna(u.loc[p, latest])] if latest in u.columns else []
    if ahead:
        st.markdown(
            f'<div style="color:#0f766e;font-size:12px;margin-top:10px;">'
            f'MAPA is ahead of UNICA for {latest} by {len(ahead)} fortnight(s): '
            f'{", ".join(ahead)}.</div>',
            unsafe_allow_html=True,
        )


def _region_control(page):
    """Whether the region picker drives the page in front of you, and if not,
    why not. It used to sit on the MAPA menu and go on applying itself
    silently everywhere else, which is how a Norte selection could end up
    looking at Centro-Sul numbers with nothing on screen saying so."""
    if page == "mapa_menu" or page.startswith("mapa:"):
        return True, ""
    if page == "mapa_recon":
        return False, ("Fixed to Centro-Sul. UNICA surveys Centre-South mills, "
                       "so Norte and Nordeste have nothing to compare against.")
    if page == "home":
        return False, "Applies to the MAPA series."
    return False, "UNICA reports Centro-Sul only, so this page has one region."


def render_sidebar(page):
    active, why = _region_control(page)
    level, region = _mapa_selected_region()
    names = [n for n, _, _ in MAPA_REGIONS] + ["State"]
    default = "State" if level == "state" else mapa_region_name(level, region)

    with st.sidebar:
        st.markdown(
            '<div style="font-size:11px;letter-spacing:.09em;text-transform:uppercase;'
            'color:#898781;margin:0 0 6px;">MAPA region</div>',
            unsafe_allow_html=True,
        )
        picked = st.pills("Region", options=names, default=default,
                          selection_mode="single", key="mapa_region_pick",
                          label_visibility="collapsed", disabled=not active)
        picked = picked or default

        chosen = None
        if picked == "State":
            states = mapa_states(load_mapa())
            current = region if level == "state" else states[0]
            state = st.selectbox("State", states, index=states.index(current),
                                 key="mapa_state_pick", disabled=not active)
            chosen = ("state", state)
        else:
            chosen = next((lvl, code) for n, lvl, code in MAPA_REGIONS if n == picked)

        # A disabled control must not quietly rewrite the selection it is
        # showing, or leaving a MAPA page would reset the region you picked.
        if active:
            st.session_state.mapa_region = chosen
        else:
            st.caption(why)


page = st.session_state.page
render_sidebar(page)

if page == "home":
    render_home()
elif page == "menu":
    render_menu()
elif page == "mapa_menu":
    render_mapa_menu()
elif page == "mapa_recon":
    render_mapa_recon()
elif page.startswith("mapa:"):
    render_mapa_dataset(page[len("mapa:"):])
elif page == "Overview":
    render_overview()
else:
    render_dataset(st.session_state.page)
