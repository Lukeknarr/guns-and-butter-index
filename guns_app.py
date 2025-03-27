import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import requests
import datetime

st.title("🔫 Guns and Butter Index")

# Country options and ISO codes
country_map = {
    "USA": "US", "CHN": "CN", "RUS": "RU", "FRA": "FR", "DEU": "DE",
    "SAU": "SA", "BRA": "BR", "IND": "IN", "IRN": "IR"
}

country = st.selectbox("Choose a Country", list(country_map.keys()))
start_year = st.slider("Start Year", 1990, 2022, 2000)
end_year = datetime.datetime.now().year - 1  # Usually latest available WB data

indicators = {
    "military": "MS.MIL.XPND.GD.ZS",
    "education": "SE.XPD.TOTL.GD.ZS",
    "health": "SH.XPD.CHEX.GD.ZS"
}

# Function to pull data from World Bank API
def get_data(country_code, indicator):
    url = f"https://api.worldbank.org/v2/country/{country_code}/indicator/{indicator}?format=json&per_page=1000"
    r = requests.get(url)
    raw = r.json()[1]
    df = pd.DataFrame(raw)[["date", "value"]].dropna()
    df["date"] = pd.to_numeric(df["date"])
    df.set_index("date", inplace=True)
    return df.sort_index()

# Pull data
code = country_map[country]
military_df = get_data(code, indicators["military"])
edu_df = get_data(code, indicators["education"])
health_df = get_data(code, indicators["health"])

# Combine and compute index
butter = edu_df["value"] + health_df["value"]
guns = military_df["value"]
df = pd.DataFrame({"Guns": guns, "Butter": butter})
df = df[(df.index >= start_year) & (df.index <= end_year)]
df["Guns_to_Butter"] = df["Guns"] / df["Butter"]

# Visualize
st.subheader("📊 Guns-to-Butter Ratio")
st.line_chart(df["Guns_to_Butter"])

st.subheader("📋 Raw Data")
st.dataframe(df.dropna())
