import mysql.connector

conn = mysql.connector.connect(
    host="localhost", port=3306, user="root",
    password="Asutosh@76098", database="people's_priority"
)
cur = conn.cursor()

# Seed PIN codes
pins = [
    ("751001","GPO Bhubaneswar","Rajmahal Square","Bhubaneswar","Khordha","Odisha","Bhubaneswar"),
    ("751002","Secretariat","Sachivalaya Marg","Bhubaneswar","Khordha","Odisha","Bhubaneswar"),
    ("751003","Unit II","Unit II","Bhubaneswar","Khordha","Odisha","Bhubaneswar"),
    ("751004","Ashok Nagar","Ashok Nagar","Bhubaneswar","Khordha","Odisha","Bhubaneswar"),
    ("751005","Vani Vihar","University Area","Bhubaneswar","Khordha","Odisha","Bhubaneswar"),
    ("751006","Saheed Nagar","Saheed Nagar","Bhubaneswar","Khordha","Odisha","Bhubaneswar"),
    ("751007","Jaydev Vihar","Jaydev Vihar","Bhubaneswar","Khordha","Odisha","Bhubaneswar"),
    ("751009","IRC Village","Nayapalli","Bhubaneswar","Khordha","Odisha","Bhubaneswar"),
    ("751010","VSS Nagar","VSS Nagar","Bhubaneswar","Khordha","Odisha","Bhubaneswar"),
    ("751012","Khandagiri","Khandagiri","Bhubaneswar","Khordha","Odisha","Bhubaneswar"),
    ("751014","Mancheswar IE","Mancheswar","Bhubaneswar","Khordha","Odisha","Bhubaneswar"),
    ("751017","Chandrasekharpur","CSpur","Bhubaneswar","Khordha","Odisha","Bhubaneswar"),
    ("751019","Niladri Vihar","Niladri Vihar","Bhubaneswar","Khordha","Odisha","Bhubaneswar"),
    ("751024","Patia","Patia Township","Bhubaneswar","Khordha","Odisha","Bhubaneswar"),
    ("751030","Infocity","Infocity Area","Bhubaneswar","Khordha","Odisha","Bhubaneswar"),
]
cur.executemany(
    "INSERT IGNORE INTO pin_code_directory (pin_code,postal_name,locality,city,district,state,mp_constituency) VALUES (%s,%s,%s,%s,%s,%s,%s)",
    pins
)
conn.commit()
print(f"PIN codes: {cur.rowcount} inserted")

# Seed budget tracker
cur.execute(
    "INSERT IGNORE INTO budget_tracker (id,constituency,financial_year,total_budget,remaining) VALUES (UUID(),'Bhubaneswar','2026-27',50000000,50000000)"
)
conn.commit()
print(f"Budget tracker: {cur.rowcount} inserted")

# Seed MP user
cur.execute(
    """INSERT IGNORE INTO users (id,phone,password_hash,name,role,home_pin_code,home_postal_name,home_city,home_district,home_state,home_constituency)
       VALUES (UUID(),'9000000001','$2b$12$LJ3m5ZQnJqGdM7xzP2FEauYYkVGQXvyMTMq1fqHr1RfQvXdVHirNi','Hon. MP Bhubaneswar','mp','751001','GPO Bhubaneswar','Bhubaneswar','Khordha','Odisha','Bhubaneswar')"""
)
conn.commit()
print(f"MP user: {cur.rowcount} inserted (phone: 9000000001, password: mp123456)")

conn.close()
print("Done!")
