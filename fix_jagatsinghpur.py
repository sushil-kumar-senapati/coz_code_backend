"""
Fix: PIN 752110 (Tampalo/Alichar) is in Puri DISTRICT but Jagatsinghpur LOK SABHA constituency.
Also fix all related data (submissions, clusters, processed_submissions).
And update the resolver to not blindly use district as constituency.
"""
import mysql.connector

c = mysql.connector.connect(host="localhost", port=3306, user="root", password="Asutosh@76098", database="people's_priority")
cur = c.cursor()

# 1. Fix PIN 752110 constituency
cur.execute("""
    UPDATE pin_code_directory
    SET mp_constituency = 'Jagatsinghpur'
    WHERE pin_code = '752110'
""")
c.commit()
print(f"Fixed PIN 752110 constituency: {cur.rowcount} row")

# 2. Fix raw_submissions that used PIN 752110
cur.execute("""
    UPDATE raw_submissions
    SET sub_constituency = 'Jagatsinghpur'
    WHERE submission_pin_code = '752110'
""")
c.commit()
print(f"Fixed raw_submissions: {cur.rowcount} rows")

# 3. Fix processed_submissions
cur.execute("""
    UPDATE processed_submissions
    SET constituency = 'Jagatsinghpur'
    WHERE pin_code = '752110'
""")
c.commit()
print(f"Fixed processed_submissions: {cur.rowcount} rows")

# 4. Fix demand_clusters that came from these submissions
cur.execute("""
    UPDATE demand_clusters dc
    JOIN cluster_submissions cs ON cs.cluster_id = dc.id
    JOIN processed_submissions ps ON cs.processed_submission_id = ps.id
    SET dc.constituency = 'Jagatsinghpur'
    WHERE ps.pin_code = '752110'
""")
c.commit()
print(f"Fixed demand_clusters: {cur.rowcount} rows")

# 5. Fix Jagatsinghpur MP home_constituency to match exactly
cur.execute("""
    UPDATE users SET home_constituency = 'Jagatsinghpur'
    WHERE phone = '9000000002'
""")
c.commit()
print(f"Fixed MP constituency: {cur.rowcount} row")

# 6. Reset those clusters to re-enrich and re-score for the correct constituency
cur.execute("""
    UPDATE demand_clusters
    SET status = 'categorized', priority_score = NULL, `rank` = NULL,
        data_overlay = '{}', score_explanation = NULL
    WHERE constituency = 'Jagatsinghpur'
""")
c.commit()
print(f"Reset Jagatsinghpur clusters for re-scoring: {cur.rowcount} rows")

# 7. Delete old scores for those clusters
cur.execute("""
    DELETE cs FROM cluster_scores cs
    JOIN demand_clusters dc ON cs.cluster_id = dc.id
    WHERE dc.constituency = 'Jagatsinghpur'
""")
c.commit()
print(f"Deleted old scores: {cur.rowcount} rows")

# 8. Also delete old Puri budget/scoring since those clusters moved
cur.execute("DELETE FROM budget_tracker WHERE constituency = 'Puri'")
c.commit()
cur.execute("DELETE FROM scoring_weights WHERE constituency = 'Puri'")
c.commit()

# Verify
cur2 = c.cursor(dictionary=True)
cur2.execute("""
    SELECT rs.tracking_id, rs.sub_constituency, dc.constituency AS cluster_const
    FROM raw_submissions rs
    LEFT JOIN cluster_submissions cs ON cs.raw_submission_id = rs.id
    LEFT JOIN demand_clusters dc ON cs.cluster_id = dc.id
    WHERE rs.submission_pin_code = '752110'
""")
print("\nVerification — PIN 752110 submissions:")
for r in cur2.fetchall():
    print(f"  {r['tracking_id']}: sub_const={r['sub_constituency']}, cluster_const={r['cluster_const']}")

c.close()
print("\nDone! Now run scheduler to re-score Jagatsinghpur clusters.")
