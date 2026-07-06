from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from app.database import get_db, fetch_one, fetch_all, execute_returning_id
from app.auth import hash_password, verify_password, create_token, get_current_user
from app.pin_resolver import resolve_pin

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ── Request / Response Models ────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    phone: str = Field(..., min_length=10, max_length=15)
    password: str = Field(..., min_length=4)
    name: str | None = None
    home_pin_code: str = Field(..., min_length=6, max_length=6)
    home_constituency: str | None = None  # User selects from dropdown


class LoginRequest(BaseModel):
    phone: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


# ── PIN Code Lookup (address only — no constituency) ─────────────────────────

@router.get("/pin-lookup/{pin_code}")
def pin_lookup(pin_code: str, conn=Depends(get_db)):
    """Look up location details from a 6-digit PIN code. Returns address only — constituency is selected separately."""
    if len(pin_code) != 6 or not pin_code.isdigit():
        raise HTTPException(status_code=400, detail="PIN code must be exactly 6 digits")
    row = resolve_pin(conn, pin_code)
    if not row:
        raise HTTPException(status_code=404, detail="Invalid PIN code — not found in India Post directory")
    return row


# ── Get Constituencies by State ──────────────────────────────────────────────

# All Lok Sabha constituencies by state (India)
STATE_CONSTITUENCIES = {
    "Odisha": [
        "Bargarh", "Sundargarh", "Sambalpur", "Keonjhar", "Mayurbhanj",
        "Balasore", "Bhadrak", "Jajpur", "Dhenkanal", "Bolangir",
        "Kalahandi", "Nabarangpur", "Kandhamal", "Cuttack", "Kendrapara",
        "Jagatsinghpur", "Puri", "Bhubaneswar", "Aska", "Berhampur", "Koraput",
    ],
    "West Bengal": [
        "Cooch Behar", "Alipurduars", "Jalpaiguri", "Darjeeling", "Raiganj",
        "Balurghat", "Maldaha Uttar", "Maldaha Dakshin", "Jangipur", "Baharampur",
        "Murshidabad", "Krishnanagar", "Ranaghat", "Bangaon", "Barrackpore",
        "Dum Dum", "Barasat", "Basirhat", "Jaynagar", "Mathurapur",
        "Diamond Harbour", "Jadavpur", "Kolkata Dakshin", "Kolkata Uttar",
        "Howrah", "Uluberia", "Sreerampur", "Hooghly", "Arambagh", "Tamluk",
        "Contai", "Ghatal", "Jhargram", "Medinipur", "Purulia", "Bankura",
        "Bishnupur", "Bardhaman Purba", "Bardhaman-Durgapur", "Asansol", "Bolpur", "Birbhum",
    ],
    "Bihar": [
        "Valmiki Nagar", "Paschim Champaran", "Purvi Champaran", "Sheohar",
        "Sitamarhi", "Madhubani", "Jhanjharpur", "Supaul", "Araria", "Kishanganj",
        "Katihar", "Purnia", "Madhepura", "Darbhanga", "Muzaffarpur", "Vaishali",
        "Gopalganj", "Siwan", "Maharajganj", "Saran", "Hajipur", "Ujiarpur",
        "Samastipur", "Begusarai", "Khagaria", "Bhagalpur", "Banka", "Munger",
        "Nalanda", "Patna Sahib", "Pataliputra", "Arrah", "Buxar", "Sasaram",
        "Karakat", "Jahanabad", "Aurangabad", "Gaya", "Nawada", "Jamui",
    ],
    "Jharkhand": [
        "Rajmahal", "Dumka", "Godda", "Chatra", "Koderma", "Giridih",
        "Dhanbad", "Ranchi", "Jamshedpur", "Singhbhum", "Khunti",
        "Lohardaga", "Palamu", "Hazaribagh",
    ],
    "Chhattisgarh": [
        "Sarguja", "Korba", "Bilaspur", "Janjgir-Champa", "Raigarh",
        "Durg", "Raipur", "Mahasamund", "Bastar", "Kanker", "Rajnandgaon",
    ],
    "Uttar Pradesh": [
        "Saharanpur", "Kairana", "Muzaffarnagar", "Bijnor", "Nagina", "Moradabad",
        "Rampur", "Sambhal", "Amroha", "Meerut", "Baghpat", "Ghaziabad",
        "Gautam Buddha Nagar", "Bulandshahr", "Aligarh", "Hathras", "Mathura",
        "Agra", "Fatehpur Sikri", "Firozabad", "Mainpuri", "Etah", "Badaun",
        "Aonla", "Bareilly", "Pilibhit", "Shahjahanpur", "Kheri", "Hardoi",
        "Misrikh", "Unnao", "Lucknow", "Mohanlalganj", "Rae Bareli", "Amethi",
        "Sultanpur", "Pratapgarh", "Farrukhabad", "Etawah", "Kannauj",
        "Kanpur", "Akbarpur", "Jalaun", "Jhansi", "Hamirpur", "Banda",
        "Fatehpur", "Kaushambi", "Phulpur", "Allahabad", "Barabanki",
        "Faizabad", "Ambedkar Nagar", "Bahraich", "Shravasti", "Gonda",
        "Domariyaganj", "Basti", "Sant Kabir Nagar", "Maharajganj",
        "Gorakhpur", "Kushi Nagar", "Deoria", "Bansgaon", "Lalganj",
        "Azamgarh", "Ghosi", "Salempur", "Ballia", "Jaunpur",
        "Machhlishahr", "Ghazipur", "Chandauli", "Varanasi", "Bhadohi",
        "Mirzapur", "Robertsganj",
    ],
    "Maharashtra": [
        "Nandurbar", "Dhule", "Jalgaon", "Raver", "Buldhana", "Akola",
        "Amravati", "Wardha", "Ramtek", "Nagpur", "Bhandara-Gondiya",
        "Gadchiroli-Chimur", "Chandrapur", "Yavatmal-Washim", "Hingoli",
        "Nanded", "Parbhani", "Jalna", "Aurangabad", "Dindori", "Nashik",
        "Palghar", "Bhiwandi", "Kalyan", "Thane", "Mumbai North",
        "Mumbai North West", "Mumbai North East", "Mumbai North Central",
        "Mumbai South Central", "Mumbai South", "Raigad", "Maval", "Pune",
        "Baramati", "Shirur", "Ahmednagar", "Shirdi", "Beed", "Osmanabad",
        "Latur", "Solapur", "Madha", "Sangli", "Satara", "Ratnagiri-Sindhudurg",
        "Kolhapur", "Hatkanangle",
    ],
    "Tamil Nadu": [
        "Tiruvallur", "Chennai North", "Chennai South", "Chennai Central",
        "Sriperumbudur", "Kancheepuram", "Arakkonam", "Vellore", "Krishnagiri",
        "Dharmapuri", "Tiruvannamalai", "Arani", "Villupuram", "Kallakurichi",
        "Salem", "Namakkal", "Erode", "Tiruppur", "Nilgiris", "Coimbatore",
        "Pollachi", "Dindigul", "Karur", "Tiruchirappalli", "Perambalur",
        "Cuddalore", "Chidambaram", "Mayiladuthurai", "Nagapattinam",
        "Thanjavur", "Sivaganga", "Madurai", "Theni", "Virudhunagar",
        "Ramanathapuram", "Thoothukudi", "Tenkasi", "Tirunelveli", "Kanyakumari",
    ],
    "Karnataka": [
        "Chikkodi", "Belgaum", "Bagalkot", "Bijapur", "Gulbarga",
        "Raichur", "Bidar", "Koppal", "Bellary", "Haveri", "Dharwad",
        "Uttara Kannada", "Davanagere", "Shimoga", "Udupi-Chikmagalur",
        "Hassan", "Dakshina Kannada", "Chitradurga", "Tumkur", "Mandya",
        "Mysore", "Chamarajanagar", "Bangalore Rural", "Bangalore North",
        "Bangalore Central", "Bangalore South", "Chikkaballapur", "Kolar",
    ],
    "Andhra Pradesh": [
        "Srikakulam", "Vizianagaram", "Visakhapatnam", "Anakapalli",
        "Amalapuram", "Rajahmundry", "Narasapuram", "Eluru", "Machilipatnam",
        "Vijayawada", "Guntur", "Narasaraopet", "Bapatla", "Ongole",
        "Nandyal", "Kurnool", "Anantapur", "Hindupur", "Kadapa",
        "Nellore", "Tirupati", "Rajampet", "Chittoor", "Araku", "Narsapuram",
    ],
    "Telangana": [
        "Adilabad", "Peddapalle", "Karimnagar", "Nizamabad", "Zahirabad",
        "Medak", "Malkajgiri", "Secunderabad", "Hyderabad", "Chevella",
        "Mahbubnagar", "Nagarkurnool", "Nalgonda", "Bhongir", "Warangal",
        "Mahabubabad", "Khammam",
    ],
    "Kerala": [
        "Kasaragod", "Kannur", "Vatakara", "Wayanad", "Kozhikode",
        "Malappuram", "Ponnani", "Palakkad", "Alathur", "Thrissur",
        "Chalakudy", "Ernakulam", "Idukki", "Kottayam", "Alappuzha",
        "Mavelikkara", "Pathanamthitta", "Kollam", "Attingal",
        "Thiruvananthapuram",
    ],
    "Rajasthan": [
        "Ganganagar", "Bikaner", "Churu", "Jhunjhunu", "Sikar", "Jaipur Rural",
        "Jaipur", "Alwar", "Bharatpur", "Karauli-Dholpur", "Dausa",
        "Tonk-Sawai Madhopur", "Ajmer", "Nagaur", "Pali", "Jodhpur",
        "Barmer", "Jalore", "Udaipur", "Banswara", "Chittorgarh",
        "Rajsamand", "Bhilwara", "Kota", "Jhalawar-Baran",
    ],
    "Gujarat": [
        "Kachchh", "Banaskantha", "Patan", "Mahesana", "Sabarkantha",
        "Gandhinagar", "Ahmedabad East", "Ahmedabad West", "Surendranagar",
        "Rajkot", "Porbandar", "Jamnagar", "Junagadh", "Amreli",
        "Bhavnagar", "Anand", "Kheda", "Panchmahal", "Dahod", "Vadodara",
        "Chhota Udaipur", "Bharuch", "Bardoli", "Surat", "Navsari", "Valsad",
    ],
    "Madhya Pradesh": [
        "Morena", "Bhind", "Gwalior", "Guna", "Sagar", "Tikamgarh",
        "Damoh", "Khajuraho", "Satna", "Rewa", "Sidhi", "Shahdol",
        "Jabalpur", "Mandla", "Balaghat", "Chhindwara", "Hoshangabad",
        "Betul", "Vidisha", "Bhopal", "Rajgarh", "Dewas", "Ujjain",
        "Mandsaur", "Ratlam", "Dhar", "Indore", "Khargone", "Khandwa",
    ],
    "Punjab": [
        "Gurdaspur", "Amritsar", "Khadoor Sahib", "Jalandhar",
        "Hoshiarpur", "Anandpur Sahib", "Ludhiana", "Fatehgarh Sahib",
        "Faridkot", "Firozpur", "Bathinda", "Sangrur", "Patiala",
    ],
    "Assam": [
        "Karimganj", "Silchar", "Autonomous District", "Dhubri", "Kokrajhar",
        "Barpeta", "Darrang-Udalguri", "Guwahati", "Mangaldoi", "Tezpur",
        "Nowgong", "Kaliabor", "Jorhat", "Dibrugarh", "Lakhimpur",
    ],
}


@router.get("/constituencies")
def get_constituencies(state: str, conn=Depends(get_db)):
    """Get list of Lok Sabha constituencies for a given state.
    First checks DB (budget_tracker), then falls back to static mapping."""
    # Try from DB first (dynamic — covers seeded constituencies)
    rows = fetch_all(conn, """
        SELECT DISTINCT constituency FROM budget_tracker
        WHERE constituency IN (
            SELECT DISTINCT home_constituency FROM users WHERE home_state = %s AND role = 'mp'
        ) ORDER BY constituency
    """, (state,))
    if rows:
        return [r["constituency"] for r in rows]

    # Fallback to static mapping
    constituencies = STATE_CONSTITUENCIES.get(state, [])
    if not constituencies:
        # Try case-insensitive match
        for k, v in STATE_CONSTITUENCIES.items():
            if k.lower() == state.lower():
                return sorted(v)
    return sorted(constituencies)


# ── Register ─────────────────────────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse, status_code=201)
def register(req: RegisterRequest, conn=Depends(get_db)):
    # Check if phone already exists
    existing = fetch_one(conn, "SELECT id FROM users WHERE phone = %s", (req.phone,))
    if existing:
        raise HTTPException(status_code=409, detail="Phone number already registered")

    # Look up PIN code for address auto-fill
    pin_data = resolve_pin(conn, req.home_pin_code)
    if not pin_data:
        raise HTTPException(status_code=400, detail="Invalid PIN code — not found in India Post directory")

    # Constituency comes from user selection (dropdown), NOT from PIN code
    constituency = req.home_constituency or pin_data.get("mp_constituency", "")

    hashed = hash_password(req.password)
    user_id = execute_returning_id(
        conn,
        """INSERT INTO users (id, phone, password_hash, name, role,
                home_pin_code, home_postal_name, home_locality, home_city,
                home_district, home_state, home_constituency)
           VALUES (%s, %s, %s, %s, 'user', %s, %s, %s, %s, %s, %s, %s)""",
        (
            req.phone, hashed, req.name or "",
            req.home_pin_code,
            pin_data["postal_name"], pin_data["locality"], pin_data["city"],
            pin_data["district"], pin_data["state"], constituency,
        ),
    )

    token = create_token(user_id, "user")
    user = fetch_one(conn, "SELECT id, phone, name, role, home_pin_code, home_city, home_district, home_state, home_constituency, total_submissions FROM users WHERE id = %s", (user_id,))
    return TokenResponse(access_token=token, user=user)


# ── Login ────────────────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, conn=Depends(get_db)):
    user = fetch_one(conn, "SELECT * FROM users WHERE phone = %s AND is_active = TRUE", (req.phone,))
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid phone or password")

    # Update last login
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET last_login_at = CURRENT_TIMESTAMP WHERE id = %s", (user["id"],))
    conn.commit()
    cursor.close()

    token = create_token(user["id"], user["role"])
    safe_user = {k: v for k, v in user.items() if k != "password_hash"}
    return TokenResponse(access_token=token, user=safe_user)


# ── Get Current User Profile ─────────────────────────────────────────────────

@router.get("/me")
def get_me(user=Depends(get_current_user)):
    safe = {k: v for k, v in user.items() if k != "password_hash"}
    return safe
