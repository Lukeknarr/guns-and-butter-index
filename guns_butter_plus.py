
import streamlit as st
import pandas as pd
import requests
import datetime
import altair as alt

st.set_page_config(layout="wide")
st.title("🔫 Guns and Butter Index – Data + Context")

INDICATORS = {
    "military": "MS.MIL.XPND.GD.ZS",
    "education": "SE.XPD.TOTL.GD.ZS",
    "health": "SH.XPD.CHEX.GD.ZS",
}

@st.cache_data(show_spinner=False)
def get_country_list():
    url = "https://api.worldbank.org/v2/country?format=json&per_page=500"
    res = requests.get(url).json()[1]
    return sorted([(c["id"], f"{c['name']} ({c['id']})") for c in res if c["region"]["value"] != "Aggregates"], key=lambda x: x[1])

def get_indicator_data(code, indicator):
    url = f"https://api.worldbank.org/v2/country/{code}/indicator/{indicator}?format=json&per_page=1000"
    res = requests.get(url).json()
    if len(res) < 2: return pd.DataFrame()
    df = pd.DataFrame(res[1])[["date", "value"]].dropna()
    df["date"] = pd.to_numeric(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df.set_index("date", inplace=True)
    return df.sort_index()

def build_metrics(code, interpolate):
    mil = get_indicator_data(code, INDICATORS["military"])
    edu = get_indicator_data(code, INDICATORS["education"])
    hlth = get_indicator_data(code, INDICATORS["health"])
    if mil.empty or edu.empty or hlth.empty: return None
    all_years = mil.index.union(edu.index).union(hlth.index)
    df = pd.DataFrame(index=all_years)
    df["Military"] = mil["value"]
    df["Education"] = edu["value"]
    df["Health"] = hlth["value"]
    df["Butter"] = df["Education"] + df["Health"]
    df["G/B Ratio"] = df["Military"] / df["Butter"]
    df = df.sort_index().astype(float)
    if interpolate:
        df = df.interpolate(limit_area="inside", limit_direction="both")
    return df

countries = get_country_list()
country_codes = [c[0] for c in countries]
code_to_name = {c[0]: c[1] for c in countries}

default = ["US", "CN", "RU"]
selected = st.multiselect("🌍 Select Countries", country_codes, default=[c for c in default if c in country_codes], format_func=lambda x: code_to_name.get(x, x))
year_range = st.slider("📅 Year Range", 1990, datetime.datetime.now().year - 1, (2000, 2022))
metrics = st.multiselect("📊 Metrics", ["Military", "Butter", "G/B Ratio"], default=["G/B Ratio"])
interpolate = st.checkbox("Allow Interpolation", value=True)

combined = []
for code in selected:
    name = code_to_name.get(code, code)
    df = build_metrics(code, interpolate)
    if df is None: continue
    df = df[(df.index >= year_range[0]) & (df.index <= year_range[1])]
    for metric in metrics:
        temp = df[[metric]].copy()
        temp["Country"] = name
        temp["Metric"] = metric
        temp = temp.rename(columns={metric: "Value"})
        combined.append(temp)

if combined:
    chart_df = pd.concat(combined).reset_index().rename(columns={"date": "Year"})
else:
    chart_df = pd.DataFrame()

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

st.subheader("📋 Raw Data")
st.dataframe(chart_df.round(2), use_container_width=True)

st.subheader("🧠 Ask for Historical Context")
q = st.text_input("Ask: e.g. Why did Colombia’s G/B Ratio spike in 2004?")
if q:
    st.markdown("**Searching historical events...**")
    # Placeholder simulated response
    st.markdown("**Example Insight:**")
    st.markdown(f"**Q:** _{q}_")
    st.markdown("**A:** In 2004, Colombia experienced increased military operations against insurgent groups. Social spending lagged behind due to budget constraints. [Wikipedia: 2004 in Colombia](https://en.wikipedia.org/wiki/2004_in_Colombia)")
