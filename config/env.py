from dotenv import load_dotenv
load_dotenv()

import os

X_API_KEY = os.getenv("X_API_KEY")
X_API_SECRET = os.getenv("X_API_SECRET")
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN")
X_CALLBACK_URL = os.getenv("X_CALLBACK_URL", "http://localhost:8000/x/callback")

GMAIL_SCOPES = os.getenv("GMAIL_SCOPES", "").split()