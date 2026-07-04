import mysql.connector
c = mysql.connector.connect(host="localhost", port=3306, user="root", password="Asutosh@76098", database="people's_priority")
cur = c.cursor(dictionary=True)

print("=== ALL RAW SUBMISSIONS (ordered by date) ===")
cur.execute("""
    SELECT rs.id, rs.tracking_id, rs.status, rs.input_type, rs.raw_text,
           rs.submission_pin_code, rs.sub_district, rs.sub_constituency,
           rs.created_at, u.name AS user_name
    FROM raw_submissions rs
    JOIN users u ON rs.user_id = u.id
    ORDER BY rs.created_at DESC
""")
for r in cur.fetchall():
    text = (r["raw_text"] or "")[:40]
    print(f"  [{r['status']:10s}] {r['tracking_id']} | {r['input_type']:6s} | PIN={r['submission_pin_code']} | {r['sub_district'] or '?':10s} | {r['sub_constituency'] or '?':15s} | {r['user_name']} | {text}")

print("\n=== SUBMISSIONS WITH STATUS='submitted' (unprocessed) ===")
cur.execute("SELECT COUNT(*) AS cnt FROM raw_submissions WHERE status = 'submitted'")
print(f"  Count: {cur.fetchone()['cnt']}")

print("\n=== ALL USERS ===")
cur.execute("SELECT id, phone, name, role, home_constituency, total_submissions FROM users")
for r in cur.fetchall():
    print(f"  {r['phone']} | {r['name']:20s} | role={r['role']} | const={r['home_constituency'] or '?'} | subs={r['total_submissions']}")

c.close()
