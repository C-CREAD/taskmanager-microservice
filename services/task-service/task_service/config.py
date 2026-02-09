import os
import sys
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Path to .env file
ENV_FILE = BASE_DIR / '.env'

def load_env():
    """Load environment variables from .env file"""
    if ENV_FILE.exists():
        with open(ENV_FILE) as f:
            for line in f:
                # Skip empty lines and comments
                line = line.strip()
                if line and not line.startswith('#'):
                    # Split on first '=' only
                    if '=' in line:
                        key, value = line.split('=', 1)
                        # Remove quotes if present
                        value = value.strip().strip('"').strip("'")
                        os.environ[key] = value
    else:
        print(f"⚠️  Warning: .env file not found at {ENV_FILE}")
        print("   Environment variables will use defaults or system env vars")

# Load .env file when this module is imported
load_env()