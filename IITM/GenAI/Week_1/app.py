import streamlit as st 
from pathlib import Path 
import pandas as pd 
import torch 
from src.data_processing import load_and_process_data
from src.train import train_model

st.set_page_config(
    page_title = "Olist Churn Predictor",
    layout = "wide",
    initial_sidebar_state = "expanded"   
)

st.title("Olist Customer Predictor")
st.markdown("Predict whether a customer will churn based on their order history.")
st.sidebar.header("Customer Inputs")

@st.cache_resource(show_spinner = "Training the model...")
def get_model_and_columns():
    X_train, X_val, X_test, y_train, y_val, y_test = load_and_process_data("data/Constructed Customer Dataset.csv")

    model = train_model(X_train, y_train, X_val, y_val, epochs = 10)
    model.eval()
    return model, list(X_train.columns), y_test, X_test

model, feature_cols, y_test, X_test = get_model_and_columns()

st.markdown("Customer Inputs")