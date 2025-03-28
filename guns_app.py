
import streamlit as st
import pandas as pd
import requests
import datetime
import altair as alt
from io import BytesIO

st.set_page_config(layout="wide")
st.title("🔫 Guns and Butter Index – Advanced Comparison Dashboard")

# -------------------------------
# 1. Constants
# -------------------------------
INDICATORS = {
    "military": "MS.MIL.XPND.GD.ZS",
    "education": "SE.XPD.TOTL.GD.ZS",
    "health": "SH.XPD.CHEX.GD.ZS",
}
REGIONAL_GROUPS = {
    "Sub-Saharan Africa": ["NG", "ZA", "KE", "ET", "GH"],
    "Europe & Central Asia": ["DE", "FR", "IT", "GB", "PL"],
    "Middle East & North Africa": ["EG", "IR", "IQ", "SA", "DZ"],
    "South Asia": ["IN", "PK", "BD", "LK", "NP"],
    "East Asia & Pacific": ["CN", "JP", "KR", "ID", "PH"],
    "Latin America & Caribbean": ["BR", "MX", "AR", "CO", "CL"],
}

# -------------------------------
# 2. Data Functions
# -------------------------------
@st.cache_data(show_spinner=False)
def get_country_list():
    url = "https://api.worldbank.org/v2/country?format=json&per_page=500"
    res = requests.get(url).json()[1]
    return sorted([(c["id"], f"{c['name']} ({c['id']})", c["region"]["value"]) for c in res if c["region"]["value"] != "Aggregates"], key=lambda x: x[1])

def get_indicator_data(country_code, indicator):
    url = f"https://api.worldbank.org/v2/country/{country_code}/indicator/{indicator}?format=json&per_page=1000"
    res = requests.get(url).json()
    if len(res) < 2:
        return pd.DataFrame()
    data = res[1]
    df = pd.DataFrame(data)[["date", "value"]].dropna()
    df["date"] = pd.to_numeric(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df.set_index("date", inplace=True)
    return df.sort_index()

def build_country_metrics(code):
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
    df = df.interpolate(limit_direction="both")
    return df

# -------------------------------
# 3. UI Controls
# -------------------------------
countries = get_country_list()
country_codes = [c[0] for c in countries]
code_to_name = {c[0]: c[1] for c in countries}
code_to_region = {c[0]: c[2] for c in countries}

default = ["US", "CN", "RU"]
selected = st.multiselect("🌍 Select Countries", country_codes, default=default, format_func=lambda x: code_to_name.get(x, x))
year_range = st.slider("Year Range", 1990, datetime.datetime.now().year - 1, (2000, 2022))

metrics = st.multiselect("📊 Metrics to Display", ["Military", "Butter", "G/B Ratio"], default=["G/B Ratio"])

# -------------------------------
# 4. Data Compilation
# -------------------------------
combined = pd.DataFrame()
long_data = []

for code in selected:
    name = code_to_name.get(code, code)
    df = build_country_metrics(code)
    if df is None: continue
    df = df.loc[(df.index >= year_range[0]) & (df.index <= year_range[1])]
    for metric in metrics:
        temp = df[[metric]].copy()
        temp["Country"] = name
        temp["Metric"] = metric
        temp = temp.rename(columns={metric: "Value"})
        long_data.append(temp)

if long_data:
    chart_df = pd.concat(long_data).reset_index().rename(columns={"date": "Year"})
else:
    chart_df = pd.DataFrame()

# -------------------------------
# 5. Altair Chart
# -------------------------------
if not chart_df.empty:
    st.subheader("📈 Interactive Chart")
    chart = alt.Chart(chart_df).mark_line().encode(
        x=alt.X("Year:O", axis=alt.Axis(labelAngle=0)),
        y="Value:Q",
        color="Country:N",
        strokeDash="Metric:N",
        tooltip=["Year", "Country", "Metric", "Value"]
    ).properties(width=1000, height=450)
    st.altair_chart(chart, use_container_width=True)

# -------------------------------
# 6. Tabs & Data Export
# -------------------------------
st.subheader("📋 Raw Data & Export")
with st.expander("Show data table"):
    st.dataframe(chart_df)

def convert_df_to_csv(df):
    return df.to_csv(index=False).encode("utf-8")

if not chart_df.empty:
    csv = convert_df_to_csv(chart_df)
    st.download_button("📥 Download CSV", csv, "guns_butter_data.csv", "text/csv")

# -------------------------------
# 7. Ask for Context
# -------------------------------
st.subheader("🧠 Ask Why Something Happened")
q = st.text_input("Ask: e.g. Why did Guyana’s G/B ratio spike in 2004?")
if q:
    st.markdown("**(Sample GPT insight):**")
    st.markdown(f"> _{q}_")
    st.markdown("Military spending increased due to regional instability, while health/education budgets remained static.")

Military spending increased due to regional instability, while health/education budgets remained static.")
