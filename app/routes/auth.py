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


class LoginRequest(BaseModel):
    phone: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


# ── PIN Code Lookup ──────────────────────────────────────────────────────────

@router.get("/pin-lookup/{pin_code}")
def pin_lookup(pin_code: str, conn=Depends(get_db)):
    """Look up location details from a 6-digit PIN code. Fetches from India Post API if not cached."""
    if len(pin_code) != 6 or not pin_code.isdigit():
        raise HTTPException(status_code=400, detail="PIN code must be exactly 6 digits")
    row = resolve_pin(conn, pin_code)
    if not row:
        raise HTTPException(status_code=404, detail="Invalid PIN code — not found in India Post directory")
    return row


# ── Register ─────────────────────────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse, status_code=201)
def register(req: RegisterRequest, conn=Depends(get_db)):
    # Check if phone already exists
    existing = fetch_one(conn, "SELECT id FROM users WHERE phone = %s", (req.phone,))
    if existing:
        raise HTTPException(status_code=409, detail="Phone number already registered")

    # Look up PIN code for auto-fill (real India Post API + cache)
    pin_data = resolve_pin(conn, req.home_pin_code)
    if not pin_data:
        raise HTTPException(status_code=400, detail="Invalid PIN code — not found in India Post directory")

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
            pin_data["district"], pin_data["state"], pin_data["mp_constituency"],
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
