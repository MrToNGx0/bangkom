import os

# Root directory
ROOT_DIR = os.getcwd()

# Data & Static directories
STATIC_DIR = os.path.join(ROOT_DIR, "web")
INPUT_DIR = os.path.join(ROOT_DIR, "input")
OUTPUT_DIR = os.path.join(ROOT_DIR, "output")
VOCAB_DIR = os.path.join(ROOT_DIR, "app", "data")

# Create directories if they don't exist
os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(VOCAB_DIR, exist_ok=True)

# Default Model settings
DEFAULT_MODEL = "large-v3-turbo"
ALLOWED_MODELS = ["base", "small", "medium", "large-v3-turbo", "large-v3"]
ALLOWED_LANGUAGES = ["auto", "th", "en", "ja", "zh"]
