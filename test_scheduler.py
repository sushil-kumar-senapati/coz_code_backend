import requests
r = requests.post("http://localhost:8000/scheduler/run")
print(f"Status: {r.status_code}")
print(r.text[:2000])
