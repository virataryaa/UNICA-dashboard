import streamlit as st
import pandas as pd

from data_loader import load_wide, year_columns, dataset_slice, dataset_registry
from charts import (monthly_comparison, cumulative_forecast,
                     min_max_avg, summary_table, ytd_comparison)
from table_html import raw_table_html, summary_table_html

st.set_page_config(page_title="UNICA: Brazil", layout="wide")

CSS = """
<style>
.stApp { background-color: #ffffff; }
.block-container { max-width: 1400px; padding-top: 3rem; }

.unica-header {
    background: linear-gradient(135deg, #0f766e 0%, #0c5b53 100%);
    padding: 18px 28px;
    border-radius: 14px;
    margin-bottom: 28px;
    box-shadow: 0 4px 16px rgba(15, 118, 110, 0.16);
}
.unica-header h1 {
    color: white;
    font-size: 21px;
    font-weight: 600;
    letter-spacing: -0.01em;
    margin: 0;
}

div[data-testid="stMetric"] { background-color: #f9f9f7; }

/* Default (menu list) buttons: clean flat rows, no boxy borders */
.stButton>button {
    background-color: transparent;
    color: #0b0b0b;
    border: none;
    border-bottom: 1px solid #ececea;
    border-radius: 0;
    width: 100%;
    padding: 14px 6px;
    text-align: left;
    font-size: 15px;
    font-weight: 500;
    transition: background-color 0.15s ease, color 0.15s ease;
}
.stButton>button:hover {
    background-color: #f9f9f7;
    color: #0f766e;
    border-bottom: 1px solid #ececea;
}
.stButton>button:disabled {
    color: #c3c2b7;
    border-bottom: 1px solid #ececea;
}

/* Back link: minimal ghost button, marked via the preceding .back-marker div */
.back-marker + div[data-testid="stButton"] button {
    background-color: transparent;
    border: none;
    color: #52514e;
    font-weight: 500;
    font-size: 14px;
    padding: 6px 10px 6px 0;
    text-align: left;
    width: auto;
}
.back-marker + div[data-testid="stButton"] button:hover {
    color: #0f766e;
    background-color: transparent;
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


DERIVED = {
    "Fuel Consumption": _compute_fuel_consumption,
    "Gasolina Consumption": _compute_gasolina_consumption,
}

MENU_ITEMS = [
    "Sugarcane Crush", "Sugar", "Ethanol", "ATR", "ATR Yield", "Sugar Mix",
    "Ethanol Sales", "Hydrous (Int)", "Anhydrous (Int)",
    "Fuel Consumption", "Gasolina Consumption", "Hydrous Share",
]


def go_to(page):
    st.session_state.page = page


def render_menu():
    st.markdown('<div class="unica-header"><h1>UNICA: Brazil</h1></div>', unsafe_allow_html=True)
    for item in MENU_ITEMS:
        disabled = item not in available and item not in DERIVED
        label = item if not disabled else f"{item} (coming soon)"
        st.button(label, key=f"menu_{item}", disabled=disabled,
                   on_click=go_to, args=(item,), use_container_width=True)


def render_dataset(name):
    st.markdown('<div class="back-marker"></div>', unsafe_allow_html=True)
    st.button("← Back to menu", on_click=go_to, args=("menu",))
    st.markdown(f'<div class="unica-header"><h1>{name}</h1></div>', unsafe_allow_html=True)

    if name in DERIVED:
        df_wide = DERIVED[name]()
        kind = "flow"
    else:
        df_wide = dataset_slice(df_wide_all, name)
        kind = kind_by_dataset.get(name, "flow")

    if df_wide.empty:
        st.info("No data loaded for this dataset yet.")
        return
    year_cols = year_columns(df_wide)
    unit = UNITS.get(name, "")

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
            st.plotly_chart(monthly_comparison(df_wide, year_cols, height=PANEL_H), use_container_width=True)
            st.plotly_chart(min_max_avg(df_wide, year_cols, height=PANEL_H), use_container_width=True)
        with cols[1]:
            st.plotly_chart(
                cumulative_forecast(df_wide, year_cols, height=2 * PANEL_H + 40),
                use_container_width=True,
            )

    bottom_cols = st.columns([1, 1, 2])
    with bottom_cols[0]:
        table, period_label = summary_table(df_wide, year_cols, kind)
        st.markdown(summary_table_html(table, period_label, unit), unsafe_allow_html=True)
    with bottom_cols[1]:
        st.plotly_chart(ytd_comparison(df_wide, year_cols, kind=kind, height=280),
                         use_container_width=True)

    st.markdown(
        raw_table_html(df_wide, year_cols, title=name, unit=unit, kind=kind),
        unsafe_allow_html=True,
    )


if st.session_state.page == "menu":
    render_menu()
else:
    render_dataset(st.session_state.page)
