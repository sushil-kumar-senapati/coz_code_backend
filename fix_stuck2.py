import mysql.connector
c = mysql.connector.connect(host="localhost", port=3306, user="root", password="Asutosh@76098", database="people's_priority")
cur = c.cursor(dictionary=True)

# Find clusters that got categorized but have no category — need re-processing
cur.execute("SELECT id, status, mplads_category_code, is_mplads_eligible FROM demand_clusters WHERE mplads_category_code IS NULL")
rows = cur.fetchall()
print(f"Clusters with NULL category: {len(rows)}")
for r in rows:
    print(f"  {r['id'][:8]}... status={r['status']} cat={r['mplads_category_code']} eligible={r['is_mplads_eligible']}")

# Fix: set them to 'forming' so the NEW categorizer assigns COMMUNITY_INFRASTRUCTURE
cur2 = c.cursor()
cur2.execute("UPDATE demand_clusters SET status = 'forming' WHERE mplads_category_code IS NULL")
c.commit()
print(f"Fixed {cur2.rowcount} clusters → status='forming'")
c.close()
