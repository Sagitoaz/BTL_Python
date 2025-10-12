# server/conftest.py
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Disable API_KEY requirement for tests
os.environ.pop("API_KEY", None)
os.environ["API_KEY"] = ""
