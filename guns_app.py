import streamlit as st
import pandas as pd
import requests
import datetime

st.set_page_config(layout="wide")
st.title("🔫 Guns and Butter Index – Multi-Country Comparison")

# -------------------------------
# 1. Constants
# -------------------------------
INDICATORS = {
    "military": "MS.MIL.XPND.GD.ZS",
    "education": "SE.XPD.TOTL.GD.ZS",
    "health": "SH.XPD.CHEX.GD.ZS",
}

# -------------------------------
# 2. Helper Functions
# -------------------------------
@st.cache_data(show_spinner=False)
def get_country_list():
    url = "https://api.worldbank.org/v2/country?format=json&per_page=500"
    res = requests.get(url).json()[1]
    return sorted([(c["id"], f"{c['name']} ({c['id']})") for c in res if c["region"]["value"] != "Aggregates"], key=lambda x: x[1])

def get_indicator_data(country_code, indicator):
    url = f"https://api.worldbank.org/v2/country/{country_code}/indicator/{indicator}?format=json&per_page=1000"
    res = requests.get(url).json()
    if len(res) < 2:
        return pd.DataFrame()
    data = res[1]
    df = pd.DataFrame(data)[["date", "value"]].dropna()
    df["date"] = pd.to_numeric(df["date"])
    df.set_index("date", inplace=True)
    return df.sort_index()

def build_country_metrics(country_code):
    mil = get_indicator_data(country_code, INDICATORS["military"])
    edu = get_indicator_data(country_code, INDICATORS["education"])
    hlth = get_indicator_data(country_code, INDICATORS["health"])
    
    if mil.empty or edu.empty or hlth.empty:
        return None

    df = pd.DataFrame(index=mil.index)
    df["Military"] = mil["value"]
    df["Butter"] = edu["value"] + hlth["value"]
    df["G/B Ratio"] = df["Military"] / df["Butter"]
    return df

# -------------------------------
# 3. Input Controls (Main Panel)
# -------------------------------
country_options = get_country_list()
all_country_codes = [code for code, _ in country_options]
code_to_name = dict(country_options)

st.subheader("🌍 Select Countries to Compare")

default_codes = [code for code in ["US", "CN", "RU"] if code in all_country_codes]
selected_countries = st.multiselect(
    "Countries:",
    options=all_country_codes,
    format_func=lambda x: code_to_name.get(x, x),
    default=default_codes
)

col1, col2, col3 = st.columns(3)
with col1:
    show_military = st.checkbox("Military Spending (% of GDP)", value=True)
with col2:
    show_butter = st.checkbox("Butter (Health + Education)", value=False)
with col3:
    show_ratio = st.checkbox("Guns-to-Butter Ratio", value=True)

year_range = st.slider(
    "Year Range:",
    min_value=1990,
    max_value=datetime.datetime.now().year - 1,
    value=(2000, 2022)
)
# -------------------------------
# 4. Build and Filter Data
# -------------------------------
st.subheader("📈 Selected Indicator(s) Over Time")

chart_data = pd.DataFrame()
missing = []

for code in selected_countries:
    country_name = code_to_name.get(code, code)
    data = build_country_metrics(code)
    if data is None:
        missing.append(country_name)
        continue

    # Filter year range
    data = data[(data.index >= year_range[0]) & (data.index <= year_range[1])]

    if show_military:
        chart_data[f"{country_name} – Military"] = data["Military"]
    if show_butter:
        chart_data[f"{country_name} – Butter"] = data["Butter"]
    if show_ratio:
        chart_data[f"{country_name} – G/B Ratio"] = data["G/B Ratio"]


if chart_data.empty:
    st.warning("No data available for the selected countries and metrics.")
else:
    st.line_chart(chart_data)

# -------------------------------
# 5. Raw Data & Warnings
# -------------------------------
with st.expander("📋 Show raw data"):
    st.dataframe(chart_data.round(2))

if missing:
    st.info(f"⚠️ No valid data for: {', '.join(missing)}")
