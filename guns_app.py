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
# 3. Sidebar Inputs
# -------------------------------
country_options = get_country_list()
all_country_codes = [code for code, _ in country_options]
code_to_name = dict(country_options)

st.sidebar.header("🌍 Country Selection")
default_codes = [code for code in ["US", "CN", "RU"] if code in all_country_codes]
selected_countries = st.sidebar.multiselect(
    "Compare countries",
    options=all_country_codes,
    format_func=lambda x: code_to_name.get(x, x),
    default=default_codes
)

st.sidebar.header("📊 Metrics to Display")
show_military = st.sidebar.checkbox("Military Spending (% of GDP)", value=True)
show_butter = st.sidebar.checkbox("Butter (Health + Education, % of GDP)", value=False)
show_ratio = st.sidebar.checkbox("Guns-to-Butter Ratio", value=True)

year_range = st.sidebar.slider("Year range", 1990, datetime.datetime.now().year - 1, (2000, 2022))

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
