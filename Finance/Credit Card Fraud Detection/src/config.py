from pathlib import Path 

# --- Paths ---
# ROOT is the project root (the folder containing src/). resolve() makes the
# path absolute so the code works regardless of where you run it from.
ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = ROOT / "data" / "raw" / "creditcard.csv"
MODELS_DIR = ROOT / "models"

# --- Cost model ---
# The whole project is framed around these two numbers. They're asymmetric
# on purpose: a missed fraud is far worse than a blocked legitimate customer.
# Every threshold choice downstream is justified against them.
COST_FN = 100.0             # $ per missed fraud (chargeback, refund, reputation)
COST_FP = 5.0               # $ per false alarm (support call, customer friction)

# --- Operational constraints ---
DAILY_REVIEW_CAPACITY = 50 # alerts per day a human team can handle
REVIEW_COST = 2.0          # $ per review (analyst time, prorated)


# --- Reproducibility ---
SEED = 1234
TEST_SIZE = 0.2
DRIFT_SPLIT = 0.5          # split test window here for the drift check