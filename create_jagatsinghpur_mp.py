"""Create Jagatsinghpur MP user + budget + scoring weights."""
from passlib.context import CryptContext
import mysql.connector

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
c = mysql.connector.connect(host="localhost", port=3306, user="root", password="Asutosh@76098", database="people's_priority")
cur = c.cursor(dictionary=True)

# Check if already exists
cur.execute("SELECT id FROM users WHERE phone = '9000000002'")
if cur.fetchone():
    print("Jagatsinghpur MP already exists")
else:
    # Insert PIN if not exists
    cur2 = c.cursor()
    cur2.execute("""
        INSERT IGNORE INTO pin_code_directory (pin_code, postal_name, locality, city, district, state, mp_constituency)
        VALUES ('754103', 'Alipingal', 'Alipingal', 'Jagatsinghpur', 'Jagatsinghapur', 'Odisha', 'Jagatsinghpur')
    """)
    c.commit()

    # Create MP user
    h = pwd.hash("mp123456")
    cur2.execute("""
        INSERT INTO users (id, phone, password_hash, name, role, home_pin_code,
            home_postal_name, home_city, home_district, home_state, home_constituency)
        VALUES (UUID(), '9000000002', %s, 'Hon. MP Jagatsinghpur', 'mp', '754103',
            'Alipingal', 'Jagatsinghpur', 'Jagatsinghapur', 'Odisha', 'Jagatsinghpur')
    """, (h,))
    c.commit()
    print("Created Jagatsinghpur MP user")

# Ensure budget tracker exists
cur.execute("SELECT id FROM budget_tracker WHERE constituency = 'Jagatsinghpur'")
if not cur.fetchone():
    cur2 = c.cursor()
    cur2.execute("""
        INSERT INTO budget_tracker (id, constituency, financial_year, total_budget, remaining)
        VALUES (UUID(), 'Jagatsinghpur', '2026-27', 50000000, 50000000)
    """)
    c.commit()
    print("Created budget_tracker for Jagatsinghpur")

# Ensure scoring weights exists
cur.execute("SELECT id FROM scoring_weights WHERE constituency = 'Jagatsinghpur' AND is_active = TRUE")
if not cur.fetchone():
    cur2 = c.cursor()
    cur2.execute("INSERT INTO scoring_weights (id, constituency, is_active) VALUES (UUID(), 'Jagatsinghpur', TRUE)")
    c.commit()
    print("Created scoring_weights for Jagatsinghpur")

c.close()
print("\nDone! Jagatsinghpur MP credentials:")
print("  Phone: 9000000002")
print("  Password: mp123456")
