import pandas as pd 
import streamlit as st 

@st.cache_data
def load_data():
    df = pd.read_csv("data/netflix_titles.csv")

    # dropping null values
    df[['rating', 'release_year', 'date_added']].isna().sum()
    df = df.dropna(subset = ['rating', 'release_year', 'date_added'])

    # dropping irrelevent columns
    df = df.drop(['show_id', 'description'], axis = 1)

    # new features
    df['duration_min'] = df['duration'].str.extract(r"(\d+) min").astype('float')
    df['seasons'] = df['duration'].str.extract(r"(\d+) Season").astype(float)
    df['date_added'] = pd.to_datetime(df['date_added'], errors = 'coerce')

    return df 