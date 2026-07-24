import streamlit as st
import pandas as pd

from data_loader import load_wide, year_columns, dataset_slice, dataset_registry
from charts import monthly_comparison, cumulative_forecast, min_max_avg, summary_table, ytd_comparison
from table_html import raw_table_html, summary_table_html

st.set_page_config(page_title="UNICA: Brazil", layout="wide")

CSS = """
<style>
.stApp { background-color: #ffffff; }
.block-container { max-width: 1500px; padding-top: 1.5rem; }
.unica-header {
    background-color: #0f766e;
    padding: 14px 24px;
    border-radius: 4px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
}
.unica-header h1 { color: white; font-size: 26px; margin: 0; }
div[data-testid="stMetric"] { background-color: #f9f9f7; }
.stButton>button {
    background-color: #f9f9f7;
    color: #0b0b0b;
    border: 1px solid #e1e0d9;
    width: 100%;
    padding: 10px;
}
.menu-btn button {
    background-color: #f9f9f7 !important;
    border: 1px solid #e1e0d9 !important;
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

if "page" not in st.session_state:
    st.session_state.page = "menu"

df_wide_all = load_wide()
registry = dataset_registry(df_wide_all)
available = set(registry["Dataset"])

MENU_ITEMS = [
    "Sugarcane Crush", "Sugar", "Ethanol", "ATR", "ATR / Cane", "Sugar Mix",
    "Ethanol Sales (Monthly)", "Hydrous (Int)", "Anhydrous (Int)",
    "Fuel Consumption", "Gasolina Consumption", "Hydrous Share",
]

UNITS = {
    "Sugarcane Crush": "MT",
    "Sugar": "MT",
    "Ethanol": "Litres",
    "ATR": "MT",
}


def go_to(page):
    st.session_state.page = page


def render_menu():
    st.markdown('<div class="unica-header"><h1>UNICA: Brazil</h1></div>', unsafe_allow_html=True)
    for item in MENU_ITEMS:
        disabled = item not in available
        label = item if not disabled else f"{item} (coming soon)"
        st.button(label, key=f"menu_{item}", disabled=disabled,
                   on_click=go_to, args=(item,), use_container_width=True)


def render_dataset(name):
    col_back, col_title, col_menu = st.columns([1, 6, 1])
    with col_back:
        st.button("< Back", on_click=go_to, args=("menu",))
    with col_title:
        st.markdown(f'<div class="unica-header"><h1>{name}</h1></div>', unsafe_allow_html=True)
    with col_menu:
        st.button("Menu", on_click=go_to, args=("menu",))

    df_wide = dataset_slice(df_wide_all, name)
    if df_wide.empty:
        st.info("No data loaded for this dataset yet.")
        return
    year_cols = year_columns(df_wide)

    PANEL_H = 330
    cols = st.columns([1, 2, 1])
    with cols[0]:
        st.plotly_chart(monthly_comparison(df_wide, year_cols, height=PANEL_H), use_container_width=True)
        st.plotly_chart(min_max_avg(df_wide, year_cols, height=PANEL_H), use_container_width=True)
    with cols[1]:
        st.plotly_chart(cumulative_forecast(df_wide, year_cols, height=2 * PANEL_H + 40),
                         use_container_width=True)
    with cols[2]:
        table, period_label = summary_table(df_wide, year_cols)
        st.markdown(summary_table_html(table, period_label), unsafe_allow_html=True)
        st.plotly_chart(ytd_comparison(df_wide, year_cols, height=PANEL_H), use_container_width=True)

    st.markdown(
        raw_table_html(df_wide, year_cols, title=name, unit=UNITS.get(name, "")),
        unsafe_allow_html=True,
    )


if st.session_state.page == "menu":
    render_menu()
else:
    render_dataset(st.session_state.page)
