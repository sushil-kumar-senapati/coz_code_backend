"""Fix constituency names and create budget/scoring_weights for new constituencies."""
import mysql.connector
from passlib.context import CryptContext

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
c = mysql.connector.connect(host="localhost", port=3306, user="root", password="Asutosh@76098", database="people's_priority")
cur = c.cursor(dictionary=True)

# 1. Fix PIN 752110 constituency from "Puri" to correct value
# Actually Puri district → Puri constituency is correct. But user says Jagatsinghpur.
# The issue is that user's HOME constituency is different from where they submitted.
# PIN 752110 = Puri district = Puri constituency. This is correct.
# User lives in Jagatsinghpur but submitted issue for Puri area.

# Fix any "X Constituency" suffixed names
cur2 = c.cursor()
cur2.execute("""
    UPDATE pin_code_directory
    SET mp_constituency = REPLACE(mp_constituency, ' Constituency', '')
    WHERE mp_constituency LIKE '% Constituency'
""")
c.commit()
print(f"Fixed {cur2.rowcount} PIN constituency names")

# Also fix in raw_submissions
cur2.execute("""
    UPDATE raw_submissions
    SET sub_constituency = REPLACE(sub_constituency, ' Constituency', '')
    WHERE sub_constituency LIKE '% Constituency'
""")
c.commit()
print(f"Fixed {cur2.rowcount} submission constituency names")

# Fix in demand_clusters
cur2.execute("""
    UPDATE demand_clusters
    SET constituency = REPLACE(constituency, ' Constituency', '')
    WHERE constituency LIKE '% Constituency'
""")
c.commit()
print(f"Fixed {cur2.rowcount} cluster constituency names")

# Fix in processed_submissions
cur2.execute("""
    UPDATE processed_submissions
    SET constituency = REPLACE(constituency, ' Constituency', '')
    WHERE constituency LIKE '% Constituency'
""")
c.commit()
print(f"Fixed {cur2.rowcount} processed submission constituency names")

# 2. Create budget_tracker for any new constituencies that don't have one
cur.execute("SELECT DISTINCT constituency FROM demand_clusters WHERE constituency IS NOT NULL")
constituencies = [r["constituency"] for r in cur.fetchall()]
for const in constituencies:
    cur.execute("SELECT id FROM budget_tracker WHERE constituency = %s", (const,))
    if not cur.fetchone():
        cur2.execute("""
            INSERT INTO budget_tracker (id, constituency, financial_year, total_budget, remaining)
            VALUES (UUID(), %s, '2026-27', 50000000, 50000000)
        """, (const,))
        c.commit()
        print(f"Created budget_tracker for: {const}")

# 3. Create scoring_weights for any new constituencies
for const in constituencies:
    cur.execute("SELECT id FROM scoring_weights WHERE constituency = %s AND is_active = TRUE", (const,))
    if not cur.fetchone():
        cur2.execute("""
            INSERT INTO scoring_weights (id, constituency, is_active)
            VALUES (UUID(), %s, TRUE)
        """, (const,))
        c.commit()
        print(f"Created scoring_weights for: {const}")

# 4. Show current state
print("\n=== Constituencies in system ===")
cur.execute("""
    SELECT dc.constituency, COUNT(*) AS clusters,
           SUM(dc.unique_users) AS total_users,
           bt.total_budget, bt.remaining
    FROM demand_clusters dc
    LEFT JOIN budget_tracker bt ON bt.constituency = dc.constituency
    GROUP BY dc.constituency, bt.total_budget, bt.remaining
""")
for r in cur.fetchall():
    budget = f"₹{r['total_budget']/10000000:.1f}Cr" if r["total_budget"] else "NO BUDGET"
    print(f"  {r['constituency']:20s} | {r['clusters']} clusters | {r['total_users']} users | {budget}")

# 5. Show which MP can see what
print("\n=== MP Users ===")
cur.execute("SELECT phone, name, home_constituency FROM users WHERE role = 'mp'")
for r in cur.fetchall():
    print(f"  {r['phone']} | {r['name']:25s} | sees: {r['home_constituency']}")

c.close()
print("\nDone!")
