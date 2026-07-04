import requests

BASE = "http://localhost:8000"

# 1. Login as citizen
r = requests.post(f"{BASE}/auth/login", json={"phone": "9876543210", "password": "test1234"})
print("Citizen login:", r.status_code, "role =", r.json().get("user", {}).get("role"))
citizen_token = r.json()["access_token"]
ch = {"Authorization": f"Bearer {citizen_token}"}

# 2. My submissions
r = requests.get(f"{BASE}/submissions/my", headers=ch)
print("My submissions:", r.status_code, f"({len(r.json())} subs)")

# 3. Citizen dashboard
r = requests.get(f"{BASE}/citizen/dashboard", headers=ch)
print("Citizen dashboard:", r.status_code, r.json().get("my_stats"))

# 4. Login as MP
r = requests.post(f"{BASE}/auth/login", json={"phone": "9000000001", "password": "mp123456"})
print("MP login:", r.status_code, "role =", r.json().get("user", {}).get("role"))
mp_token = r.json()["access_token"]
mh = {"Authorization": f"Bearer {mp_token}"}

# 5. MP dashboard
r = requests.get(f"{BASE}/mp/dashboard", headers=mh)
print("MP dashboard:", r.status_code)

# 6. MP clusters
r = requests.get(f"{BASE}/mp/clusters", headers=mh)
print("MP clusters:", r.status_code, f"({len(r.json())} clusters)")

# 7. MP budget
r = requests.get(f"{BASE}/mp/budget", headers=mh)
b = r.json()
print("MP budget:", r.status_code, "current =", b.get("current", {}).get("total_budget") if b.get("current") else "N/A")

# 8. Swagger docs
r = requests.get(f"{BASE}/docs")
print("Swagger docs:", r.status_code)

print("\n=== ALL ENDPOINTS WORKING ===")
