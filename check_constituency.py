import requests
# Check what constituency PIN 752110 actually maps to
for pin in ["752110", "754105", "754103"]:
    r = requests.get(f"http://localhost:8000/auth/pin-lookup/{pin}")
    d = r.json()
    print(f"  {pin}: {d.get('postal_name','?'):20s} | {d.get('district','?'):15s} | {d.get('mp_constituency','?')}")
