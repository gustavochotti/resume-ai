# tests/conftest.py
from dotenv import load_dotenv

def pytest_configure(config):
    load_dotenv()