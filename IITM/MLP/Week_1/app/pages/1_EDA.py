import streamlit as st
import plotly.express as px
from utils.data_loader import load_data

st.header("🔍 Exploratory Data Analysis")
df = load_data()

num_col = st.selectbox("Pick a numeric column",
                       ["release_year", "duration_min", "seasons", "content_age"])
fig = px.histogram(df.dropna(subset=[num_col]), x=num_col, nbins=30,
                   title=f"Distribution of {num_col}")
st.plotly_chart(fig, use_container_width=True)

numeric = df.select_dtypes("number")
corr = numeric.corr()
fig2 = px.imshow(corr, text_auto=".2f", color_continuous_scale="RdBu",
                 title="Correlation Matrix")
st.plotly_chart(fig2, use_container_width=True)

cat_col = st.selectbox("Group by", ["type", "rating", "is_mature", "is_family"])
fig3 = px.box(df, x=cat_col, y="duration_min", title=f"Duration by {cat_col}")
st.plotly_chart(fig3, use_container_width=True)
