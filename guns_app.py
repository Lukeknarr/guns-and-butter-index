import streamlit as st
import pandas as pd
import requests
import datetime

st.set_page_config(layout="wide")
st.title("🔫 Guns and Butter Index – Multi-Country Comparison")

# -------------------------------
# 1. Constants & region presets
# -------------------------------
INDICATORS = {
    "military": "MS.MIL.XPND.GD.ZS",
    "education": "SE.XPD.TOTL.GD.ZS",
    "health": "SH.XPD.CHEX.GD.ZS",
}

REGIONS = {
    "G7": ["US", "GB", "DE", "FR", "IT", "JP", "CA"],
    "BRICS": ["CN", "IN", "RU", "ZA", "BR"],
    "MENA": ["EG", "IR", "IQ", "JO", "LB", "DZ", "MA", "SA", "SY", "TN", "YE"],
    "Sub-Saharan Africa": ["NG", "ZA", "KE", "ET", "GH", "UG", "TZ", "SN", "BW", "RW"]
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

def build_guns_butter_df(country_code):
    try:
        mil = get_indicator_data(country_code, INDICATORS["military"])
        edu = get_indicator_data(country_code, INDICATORS["education"])
        hlth = get_indicator_data(country_code, INDICATORS["health"])
        if mil.empty or edu.empty or hlth.empty:
            return None
        butter = edu["value"] + hlth["value"]
        df = pd.DataFrame({
            "Guns": mil["value"],
            "Butter": butter,
        })
        df["G/B Ratio"] = df["Guns"] / df["Butter"]
        return df[["G/B Ratio"]]
    except:
        return None

# -------------------------------
# 3. Sidebar Inputs
# -------------------------------
country_options = get_country_list()
all_country_codes = [code for code, _ in country_options]
code_to_name = dict(country_options)

st.sidebar.header("🔍 Country Selection")
mode = st.sidebar.radio("Compare by:", ["Manual", "Region"])

if mode == "Manual":
    selected = st.sidebar.multiselect("Select countries to compare", options=all_country_codes, format_func=lambda x: code_to_name.get(x, x), default=["US", "CN", "RU"])
else:
    region = st.sidebar.selectbox("Choose a region", list(REGIONS.keys()))
    selected = REGIONS[region]

year_range = st.sidebar.slider("Year range", 1990, datetime.datetime.now().year - 1, (2000, 2022))

# -------------------------------
# 4. Main Chart
# -------------------------------
st.subheader("📈 Guns-to-Butter Ratio Over Time")

combined = pd.DataFrame()
for code in selected:
    data = build_guns_butter_df(code)
    if data is not None:
        country_name = code_to_name.get(code, code)
        combined[country_name] = data["G/B Ratio"]

filtered = combined[(combined.index >= year_range[0]) & (combined.index <= year_range[1])]
if filtered.empty:
    st.warning("No data available for the selected countries and time range.")
else:
    st.line_chart(filtered)

# -------------------------------
# 5. Raw Data Display
# -------------------------------
with st.expander("📊 Show raw data"):
    st.dataframe(filtered.round(2))
