import requests

pins = ["110001","400001","560001","600001","700001","302001","226001","380001","500001","752110"]
for p in pins:
    r = requests.get(f"http://localhost:8000/auth/pin-lookup/{p}")
    d = r.json()
    postal = d.get("postal_name", "?")
    dist = d.get("district", "?")
    state = d.get("state", "?")
    const = d.get("mp_constituency", "?")
    print(f"  {p}: {postal:20s} | {dist:20s} | {state:15s} | {const}")
