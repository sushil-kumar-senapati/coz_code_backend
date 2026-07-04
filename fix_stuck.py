import mysql.connector
c = mysql.connector.connect(host="localhost", port=3306, user="root", password="Asutosh@76098", database="people's_priority")
cur = c.cursor()
# Fix stuck clusters: set them back to 'forming' so categorizer picks them up
cur.execute("""
    UPDATE demand_clusters
    SET status = 'forming', mplads_category_code = NULL, is_mplads_eligible = NULL
    WHERE mplads_category_code IS NULL AND status = 'categorized'
""")
c.commit()
print(f"Reset {cur.rowcount} stuck clusters")
c.close()
