from pathlib import Path 

ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
DB_PATH = DATA_DIR / "olist.db"

TESTS_DIR = ROOT / "tests"
QUESTIONS_PATH = TESTS_DIR / "questions.json"
RESULTS_PATH = TESTS_DIR / "results"
LOGS_DIR = TESTS_DIR / "log"

DEFAULT_MODEL = "llama-3.3-70b-versatile"
OLLAMA_MODEL = "llama3.2"
LLM_TEMPERATURE = 0.0 
MAX_RETRIES = 2 

FORBIDDEN_KEYWORDS = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE", "TRUNCATE", "REPLACE", "ATTACH", "DETACH", "PRAGMA"]