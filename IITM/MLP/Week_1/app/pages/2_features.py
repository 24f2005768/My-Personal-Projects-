import streamlit as st
import plotly.express as px
from utils.data_loader import load_data

st.header("🛠️ Engineered Features")
df = load_data()

feature_cols = ["is_long_movie", "is_short_movie", "is_multi_season",
                "is_international", "is_drama", "is_us", "is_india",
                "is_mature", "is_family", "is_multi_country"]

available = [c for c in feature_cols if c in df.columns]

if not available:
    st.warning("Feature columns not found. Run the Day 3 feature engineering script first.")
    st.stop()

counts = df[available].sum().sort_values(ascending=False).reset_index()
counts.columns = ["Feature", "Count"]
fig = px.bar(counts, x="Count", y="Feature", orientation="h",
             title="Engineered Feature Prevalence", color="Count",
             color_continuous_scale="Viridis")
fig.update_layout(yaxis=dict(autorange="reversed"))
st.plotly_chart(fig, use_container_width=True)

st.subheader("Feature Comparison by Content Type")
sel = st.multiselect("Compare features", available,
                     default=available[:2])
for f in sel:
    ct = df.groupby(["type", f]).size().reset_index(name="Count")
    fig2 = px.bar(ct, x=f, y="Count", color="type", barmode="group",
                  title=f"{f} by Type")
    st.plotly_chart(fig2, use_container_width=True)