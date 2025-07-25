import os
from dotenv import load_dotenv

load_dotenv(override=True)

# Load from .env or environment variables
APP_ID = os.getenv("LARK_APP_ID")
APP_SECRET = os.getenv("LARK_APP_SECRET")
VERIFICATION_TOKEN = os.getenv("VERIFICATION_TOKEN")
# THREAD_ID = os.getenv("THREAD_ID")