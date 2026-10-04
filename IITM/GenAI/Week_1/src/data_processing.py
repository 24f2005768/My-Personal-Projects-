import pandas as pd 
from sklearn.model_selection import train_test_split 
from sklearn.preprocessing import StandardScaler
from pathlib import Path

def load_and_process_data(csv_path):
    try:
        current_dir = Path(__file__).resolve().parent
    except NameError:
        current_dir = Path.cwd() # Falls back to current working directory in Notebooks

    parent_dir = current_dir.parent

    # print(current_dir)
    # print(parent_dir)

    csv_path = parent_dir /  'data' / 'Constructed Customer Dataset.csv'
    df = pd.read_csv(csv_path)

    print(f'Head of df {df.head(2)}')

    print(f'Shape of the df {df.shape}')

    df['label'].value_counts(normalize=True)

    df = df.drop(columns=['customer_unique_id'], errors='ignore')

    X = df.drop('label', axis = 1)
    y = df['label']

    X = pd.get_dummies(X, columns=['city', 'state'], drop_first=True)

    X_train, X_temp, y_train, y_temp = train_test_split(X, y, test_size=0.3, stratify=y, random_state=1234)
    X_val, X_test, y_val, y_test = train_test_split(X_temp, y_temp, test_size=0.5, stratify=y_temp, random_state=1234)

    scaler = StandardScaler()
    num_cols = X_train.select_dtypes(include=['float64', 'int64']).columns
    X_train[num_cols] = scaler.fit_transform(X_train[num_cols])
    X_val[num_cols] = scaler.transform(X_val[num_cols])
    X_test[num_cols] = scaler.transform(X_test[num_cols])

    return X_train, X_val, X_test, y_train, y_val, y_test