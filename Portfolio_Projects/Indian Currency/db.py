import os
import kagglehub

# Specify the desired download directory (E drive)
os.environ["KAGGLEHUB_CACHE"] = r"E:\kagglehub_cache"

# Re-run the download, it will be saved to the E drive
path = kagglehub.dataset_download("preetrank/indian-currency-real-vs-fake-notes-dataset")
print("Path to dataset files:", path)