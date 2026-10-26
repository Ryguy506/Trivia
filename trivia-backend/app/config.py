"""Loads .env once. Import settings from here instead of calling load_dotenv/os.getenv elsewhere."""
import os

from dotenv import load_dotenv

load_dotenv()  # also exposes LANGSMITH_* to LangChain, which reads them from the environment itself

TOKEN_ROUTER_API_KEY = os.getenv("TOKEN_ROUTER_API_KEY")
BASE_URL = os.getenv("BASE_URL")
