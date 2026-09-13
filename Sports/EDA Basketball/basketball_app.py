import streamlit as st
import pandas as pd
import base64
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

st.title('WNBA Draft Pick Stats Explorer')

st.markdown("""
This app explores WNBA draft pick statistics!
* **Python libraries:** base64, pandas, streamlit, matplotlib, seaborn
* **Data source:** WNBA Draft dataset (wnbadraft.csv)
""")

st.sidebar.header('User Input Features')

# Load the data once
@st.cache_data
def load_data():
    df = pd.read_csv('wnbadraft.csv')
    return df

playerstats = load_data()

# Sidebar - Year selection
sorted_unique_year = sorted(playerstats.year.unique(), reverse=True)
selected_year = st.sidebar.multiselect('Draft Year', sorted_unique_year, sorted_unique_year)

# Sidebar - Team selection
sorted_unique_team = sorted(playerstats.team.unique())
selected_team = st.sidebar.multiselect('Team', sorted_unique_team, sorted_unique_team)

# Sidebar - College selection (top colleges)
top_colleges = playerstats.college.value_counts().head(20).index.tolist()
selected_college = st.sidebar.multiselect('College (Top 20)', sorted(top_colleges), sorted(top_colleges))

# Filtering data
df_selected = playerstats[
    (playerstats.year.isin(selected_year)) &
    (playerstats.team.isin(selected_team)) &
    (playerstats.college.isin(selected_college))
]

st.header('Display Draft Pick Stats')
st.write('Data Dimension: ' + str(df_selected.shape[0]) + ' rows and ' + str(df_selected.shape[1]) + ' columns.')
st.dataframe(df_selected)

# Download data
def filedownload(df):
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="wnba_draft_stats.csv">Download CSV File</a>'
    return href

st.markdown(filedownload(df_selected), unsafe_allow_html=True)

# Heatmap
if st.button('Intercorrelation Heatmap'):
    st.header('Intercorrelation Matrix Heatmap')
    
    # Select only numeric columns for correlation
    numeric_df = df_selected.select_dtypes(include=[np.number])
    
    if numeric_df.shape[1] < 2:
        st.warning("Not enough numeric columns to create a heatmap.")
    else:
        corr = numeric_df.corr()
        mask = np.zeros_like(corr, dtype=bool)
        mask[np.triu_indices_from(mask)] = True
        
        with sns.axes_style("white"):
            f, ax = plt.subplots(figsize=(10, 8))
            sns.heatmap(corr, mask=mask, vmax=1, vmin=-1, square=True,
                        annot=True, fmt=".2f", cmap="coolwarm", ax=ax)
        st.pyplot(f)