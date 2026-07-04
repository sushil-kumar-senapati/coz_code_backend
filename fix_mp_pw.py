from passlib.context import CryptContext
import mysql.connector

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
h = pwd.hash("mp123456")
print("Hash:", h)

c = mysql.connector.connect(host="localhost", port=3306, user="root", password="Asutosh@76098", database="people's_priority")
cur = c.cursor()
cur.execute("UPDATE users SET password_hash = %s WHERE phone = %s", (h, "9000000001"))
c.commit()
print(f"Updated MP password: {cur.rowcount} row")
c.close()
