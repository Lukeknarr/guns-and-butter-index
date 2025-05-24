import streamlit as st
import pandas as pd
import requests
import datetime
import altair as alt
import re

st.set_page_config(layout="wide")
st.title("Guns and Butter Index")

# ===============================
# 1. Constants
# ===============================
INDICATORS = {
    "military": "MS.MIL.XPND.GD.ZS",
    "education": "SE.XPD.TOTL.GD.ZS",
    "health": "SH.XPD.CHEX.GD.ZS",
}

# ===============================
# 2. Data Functions
# ===============================
@st.cache_data(show_spinner=False)
def get_country_list():
    url = "https://api.worldbank.org/v2/country?format=json&per_page=500"
    res = requests.get(url).json()[1]
    return {c["id"]: {"name": c["name"], "region": c["region"]["value"]}
            for c in res if c["region"]["value"] != "Aggregates"}

def get_indicator_data(code, indicator):
    url = f"https://api.worldbank.org/v2/country/{code}/indicator/{indicator}?format=json&per_page=1000"
    res = requests.get(url).json()
    if len(res) < 2:
        return pd.DataFrame()
    df = pd.DataFrame(res[1])[["date", "value"]].dropna()
    df["date"] = pd.to_numeric(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df.set_index("date", inplace=True)
    return df.sort_index()

def build_metrics(code, allow_interpolation):
    mil = get_indicator_data(code, INDICATORS["military"])
    edu = get_indicator_data(code, INDICATORS["education"])
    hlth = get_indicator_data(code, INDICATORS["health"])
    if mil.empty or edu.empty or hlth.empty:
        return None
    all_years = mil.index.union(edu.index).union(hlth.index)
    df = pd.DataFrame(index=all_years)
    df["Military"] = mil["value"]
    df["Education"] = edu["value"]
    df["Health"] = hlth["value"]
    df["Butter"] = df["Education"] + df["Health"]
    df["G/B Ratio"] = df["Military"] / df["Butter"]
    df = df.sort_index().astype(float)
    df.index.name = "Year"
    df["Source"] = "Real"
    if allow_interpolation:
        df_interpolated = df.interpolate(limit_area="inside", limit_direction="both")
        for col in ["Military", "Education", "Health", "Butter", "G/B Ratio"]:
            mask = df[col].isna() & df_interpolated[col].notna()
            df_interpolated.loc[mask, "Source"] = "Interpolated"
        df = df_interpolated
    return df

# ===============================
# 3. UI Controls
# ===============================
st.subheader("Input Controls")

country_data = get_country_list()
all_country_codes = list(country_data.keys())

def display_country(code):
    info = country_data.get(code, {})
    return f"{info.get('name', code)} ({code})"

col1, col2 = st.columns([3, 1])
with col1:
    default_codes = [code for code in ["US", "CN", "RU"] if code in all_country_codes]
    selected_codes = st.multiselect(
        "Select Countries:", 
        options=all_country_codes, 
        default=default_codes, 
        format_func=display_country
    )

with col2:
    year_range = st.slider(
        "Select Year Range:", 
        1990, 
        datetime.datetime.now().year - 1, 
        (2000, 2022)
    )

col3, col4 = st.columns([2, 2])
with col3:
    metrics_selected = st.multiselect(
        "Select Metrics to Display:", 
        ["Military", "Butter", "G/B Ratio"], 
        default=["G/B Ratio"]
    )
    
with col4:
    col4a, col4b = st.columns(2)
    with col4a:
        allow_interpolation = st.checkbox(
            "Allow Interpolation", 
            value=True, 
            help="Fill in missing values between real data points"
        )
    with col4b:
        show_only_real = st.checkbox(
            "Only Real Data", 
            value=False, 
            help="Exclude interpolated values"
        )

# ===============================
# 4. Data Processing
# ===============================
data_list = []
chart_df = pd.DataFrame()  # Initialize empty DataFrame

if selected_codes:  # Only process if countries are selected
    for code in selected_codes:
        name = country_data.get(code, {}).get("name", code)
        df = build_metrics(code, allow_interpolation)
        if df is None:
            continue
        df = df[(df.index >= year_range[0]) & (df.index <= year_range[1])]
        if show_only_real:
            df = df[df["Source"] == "Real"]
        for metric in metrics_selected:
            temp = df[[metric, "Source"]].copy()
            temp["Country"] = name
            temp["Metric"] = metric
            temp = temp.reset_index()  # creates "Year" column
            temp["Year"] = pd.to_numeric(temp["Year"], errors="coerce").astype(int)
            temp = temp.rename(columns={metric: "Value"})
            data_list.append(temp)
    
    if data_list:  # Only concatenate if we have data
        chart_df = pd.concat(data_list)

# ===============================
# 5. Visualization
# ===============================
if not chart_df.empty:
    st.subheader("Interactive Chart")
    chart = alt.Chart(chart_df).mark_line().encode(
        x=alt.X("Year:Q", axis=alt.Axis(labelAngle=0)),
        y="Value:Q",
        color="Country:N",
        strokeDash="Metric:N",
        tooltip=["Year", "Country", "Metric", "Value", "Source"]
    ).properties(width=1000, height=450)
    st.altair_chart(chart, use_container_width=True)
else:
    if not selected_codes:
        st.info("Please select one or more countries to display data.")
    else:
        st.warning("No data available for the selected options.")

# ===============================
# 6. Data Export
# ===============================
st.subheader("Data Export")
if not chart_df.empty:
    csv = chart_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download CSV (with Source Type)", 
        csv, 
        "guns_butter_data.csv", 
        "text/csv"
    )
else:
    if not selected_codes:
        st.info("Select countries to enable data export.")
    else:
        st.info("No data available for export with current selection.")

# End of file
