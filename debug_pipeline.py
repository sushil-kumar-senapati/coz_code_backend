import mysql.connector
c = mysql.connector.connect(host="localhost", port=3306, user="root", password="Asutosh@76098", database="people's_priority")
cur = c.cursor(dictionary=True)

print("=== DEMAND CLUSTERS ===")
cur.execute("SELECT id, mplads_category_code, is_mplads_eligible, status, unique_users, representative_text FROM demand_clusters")
for r in cur.fetchall():
    print(f"  [{r['status']:12s}] cat={str(r['mplads_category_code']):25s} eligible={r['is_mplads_eligible']} users={r['unique_users']} | {str(r['representative_text'] or '')[:60]}")

print("\n=== PROCESSED SUBMISSIONS (latest 5) ===")
cur.execute("SELECT ps.id, ps.status, ps.is_spam, ps.cluster_id, ps.translated_text_en FROM processed_submissions ps ORDER BY ps.created_at DESC LIMIT 5")
for r in cur.fetchall():
    print(f"  [{r['status']:10s}] spam={r['is_spam']} cluster={str(r['cluster_id'] or 'NONE')[:8]} | {str(r['translated_text_en'] or '')[:60]}")

print("\n=== RAW SUBMISSIONS (latest 5) ===")
cur.execute("SELECT id, tracking_id, status, input_type, raw_text FROM raw_submissions ORDER BY created_at DESC LIMIT 5")
for r in cur.fetchall():
    print(f"  [{r['status']:10s}] {r['tracking_id']} type={r['input_type']} | {str(r['raw_text'] or '')[:50]}")

c.close()
