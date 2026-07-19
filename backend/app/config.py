from pathlib import Path

# Root Directory
BASE_DIR = Path(__file__).resolve().parents[2]

# Data Directories
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
MODELS_DIR = DATA_DIR / "models"

# Dataset Files
TRAIN_FILE = RAW_DATA_DIR / "m5_train.parquet"
TEST_FILE = RAW_DATA_DIR / "m5_test.parquet"
SELL_PRICES_FILE = RAW_DATA_DIR / "m5_sell_prices.csv"
XREGS_FILE = RAW_DATA_DIR / "m5_xregs.csv"