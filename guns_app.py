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

st.sidebar.header("🔍 Select Countries")
default_codes = [code for code in ["US", "CN", "RU"] if code in all_country_codes]
selected = st.sidebar.multiselect(
    "Compare countries",
    options=all_country_codes,
    format_func=lambda x: code_to_name.get(x, x),
    default=default_codes
)

year_range = st.sidebar.slider("Year range", 1990, datetime.datetime.now().year - 1, (2000, 2022))

# -------------------------------
# 4. Main Chart
# -------------------------------
st.subheader("📈 Guns-to-Butter Ratio Over Time")

combined = pd.DataFrame()
missing = []

for code in selected:
    data = build_guns_butter_df(code)
    if data is not None:
        country_name = code_to_name.get(code, code)
        combined[country_name] = data["G/B Ratio"]
    else:
        missing.append(code_to_name.get(code, code))

filtered = combined[(combined.index >= year_range[0]) & (combined.index <= year_range[1])]
if filtered.empty:
    st.warning("No data available for the selected countries and time range.")
else:
    st.line_chart(filtered)

# -------------------------------
# 5. Raw Data + Missing Info
# -------------------------------
with st.expander("📊 Show raw data"):
    st.dataframe(filtered.round(2))

if missing:
    st.info(f"No valid data for: {', '.join(missing)}")
