import requests, os
from dotenv import load_dotenv
load_dotenv(override=True)
api_key = os.getenv("GEMINI_API_KEY")
resp = requests.get(f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}")
print(resp.json())
