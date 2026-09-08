import requests

resp = requests.post("http://localhost:8000/api/parse/", json={"content": "John Doe, experienced python dev..."})
print(f"Status: {resp.status_code}")
print(resp.text)
