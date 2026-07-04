"""
PIN Code Resolver — fetches from India Post API and caches in pin_code_directory.
Works for ALL 30,000+ Indian PIN codes.

API: https://api.postalpincode.in/pincode/{pincode}
Response: [{ "Status": "Success", "PostOffice": [{ "Name", "District", "State", ... }] }]

For constituency mapping: We use a static dataset mapping district → Lok Sabha constituency.
"""

import logging
import urllib.request
import json

log = logging.getLogger("pin_resolver")

# District → Lok Sabha constituency mapping (major ones for demo)
# In production, load full mapping from Election Commission dataset
DISTRICT_CONSTITUENCY_MAP = {
    # Odisha
    "Khordha": "Bhubaneswar", "Cuttack": "Cuttack", "Puri": "Puri",
    "Ganjam": "Berhampur", "Balasore": "Balasore", "Sambalpur": "Sambalpur",
    "Mayurbhanj": "Mayurbhanj", "Kalahandi": "Kalahandi", "Koraput": "Koraput",
    "Sundargarh": "Sundargarh", "Kendujhar": "Keonjhar", "Jajpur": "Jajpur",
    "Bargarh": "Bargarh", "Bolangir": "Bolangir", "Dhenkanal": "Dhenkanal",
    "Bhadrak": "Bhadrak", "Nabarangpur": "Nabarangpur", "Aska": "Aska",
    "Kandhamal": "Kandhamal", "Jagatsinghpur": "Jagatsinghpur",
    "Nayagarh": "Aska",
    # Major cities / metros
    "New Delhi": "New Delhi", "North Delhi": "North Delhi", "South Delhi": "South Delhi",
    "East Delhi": "East Delhi", "West Delhi": "West Delhi", "North West Delhi": "North West Delhi",
    "North East Delhi": "North East Delhi", "Central Delhi": "Chandni Chowk",
    "Mumbai": "Mumbai North", "Mumbai Suburban": "Mumbai North Central",
    "Thane": "Thane", "Pune": "Pune", "Nagpur": "Nagpur",
    "Bangalore": "Bangalore South", "Bangalore Urban": "Bangalore Central",
    "Bengaluru Urban": "Bangalore Central", "Bengaluru Rural": "Bangalore Rural",
    "Chennai": "Chennai South", "Hyderabad": "Hyderabad", "Rangareddy": "Chevella",
    "Kolkata": "Kolkata Dakshin", "North 24 Parganas": "Barasat",
    "Lucknow": "Lucknow", "Varanasi": "Varanasi", "Kanpur Nagar": "Kanpur",
    "Jaipur": "Jaipur", "Patna": "Patna Sahib", "Bhopal": "Bhopal",
    "Ahmedabad": "Ahmedabad East", "Surat": "Surat", "Indore": "Indore",
    "Coimbatore": "Coimbatore", "Madurai": "Madurai", "Visakhapatnam": "Visakhapatnam",
    "Guwahati": "Guwahati", "Kamrup Metropolitan": "Guwahati",
    "Ernakulam": "Ernakulam", "Thiruvananthapuram": "Thiruvananthapuram",
    "Chandigarh": "Chandigarh", "Dehradun": "Dehradun", "Goa": "North Goa",
    "Raipur": "Raipur", "Ranchi": "Ranchi", "Bhubaneswar": "Bhubaneswar",
    "Shimla": "Shimla", "Jammu": "Jammu", "Srinagar": "Srinagar",
    "Imphal West": "Inner Manipur", "Imphal East": "Inner Manipur",
    "Aizawl": "Mizoram", "Kohima": "Nagaland", "Gangtok": "Sikkim",
    "Itanagar": "Arunachal West", "Agartala": "Tripura West",
}


def _fetch_from_api(pin_code: str) -> dict | None:
    """Fetch PIN code details from India Post API."""
    url = f"https://api.postalpincode.in/pincode/{pin_code}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "PeoplesPriorities/1.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())

        if not data or data[0].get("Status") != "Success":
            return None

        offices = data[0].get("PostOffice", [])
        if not offices:
            return None

        # Use the first post office entry
        po = offices[0]
        district = po.get("District", "")
        state = po.get("State", "")
        # IMPORTANT: In India, district ≠ Lok Sabha constituency.
        # One district can span multiple constituencies (e.g., Puri district
        # has parts in both Puri and Jagatsinghpur Lok Sabha constituencies).
        # The mapping below is approximate. For production, use Election
        # Commission's official PIN-to-constituency dataset.
        constituency = DISTRICT_CONSTITUENCY_MAP.get(district, district)

        return {
            "pin_code": pin_code,
            "postal_name": po.get("Name", ""),
            "locality": po.get("Name", ""),
            "city": po.get("Block", "") or po.get("Division", "") or district,
            "district": district,
            "state": state,
            "mp_constituency": constituency,
        }
    except Exception as e:
        log.warning(f"PIN API failed for {pin_code}: {e}")
        return None


def resolve_pin(conn, pin_code: str) -> dict | None:
    """
    Look up PIN code: first check local DB, then fetch from India Post API.
    If fetched from API, cache it in pin_code_directory for future use.
    """
    from app.database import fetch_one, execute

    # 1. Check local cache
    row = fetch_one(conn, "SELECT * FROM pin_code_directory WHERE pin_code = %s", (pin_code,))
    if row:
        return row

    # 2. Fetch from India Post API
    data = _fetch_from_api(pin_code)
    if not data:
        return None

    # 3. Cache in DB for future lookups
    try:
        execute(conn, """
            INSERT IGNORE INTO pin_code_directory
                (pin_code, postal_name, locality, city, district, state, mp_constituency)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            data["pin_code"], data["postal_name"], data["locality"],
            data["city"], data["district"], data["state"], data["mp_constituency"],
        ))
        log.info(f"Cached PIN {pin_code}: {data['postal_name']}, {data['district']}, {data['state']}")
    except Exception as e:
        log.warning(f"Failed to cache PIN {pin_code}: {e}")

    return data
