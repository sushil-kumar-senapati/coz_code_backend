import mysql.connector
c = mysql.connector.connect(host="localhost", port=3306, user="root", password="Asutosh@76098", database="people's_priority")
cur = c.cursor(dictionary=True)
cur.execute("SELECT media_type, file_url, file_name, file_size_bytes, mime_type FROM submission_media")
rows = cur.fetchall()
if not rows:
    print("No media files in DB yet")
else:
    for r in rows:
        print(f"  {r['media_type']:6s} | {r['file_size_bytes'] or 0:>8} bytes | {r['file_url']} | {r['mime_type']}")
c.close()
