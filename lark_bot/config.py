import os
from dotenv import load_dotenv
from datetime import datetime
load_dotenv(override=True)

# Load from .env or environment variables
APP_ID = os.getenv("LARK_APP_ID")
APP_SECRET = os.getenv("LARK_APP_SECRET")
VERIFICATION_TOKEN = os.getenv("VERIFICATION_TOKEN")
DATE_NOW = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
# THREAD_ID = os.getenv("THREAD_ID")
