import mysql.connector
from mysql.connector import pooling
from app.config import get_settings

_pool = None


def get_pool():
    global _pool
    if _pool is None:
        s = get_settings()
        _pool = pooling.MySQLConnectionPool(
            pool_name="pp_pool",
            pool_size=10,
            host=s.DB_HOST,
            port=s.DB_PORT,
            user=s.DB_USER,
            password=s.DB_PASSWORD,
            database=s.DB_NAME,
            charset="utf8mb4",
            collation="utf8mb4_unicode_ci",
            autocommit=False,
        )
    return _pool


def get_db():
    """FastAPI dependency — yields a connection, auto-closes after request."""
    conn = get_pool().get_connection()
    try:
        yield conn
    finally:
        conn.close()


def fetch_one(conn, query: str, params: tuple = ()):
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query, params)
    row = cursor.fetchone()
    cursor.close()
    return row


def fetch_all(conn, query: str, params: tuple = ()):
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query, params)
    rows = cursor.fetchall()
    cursor.close()
    return rows


def execute(conn, query: str, params: tuple = ()):
    cursor = conn.cursor()
    cursor.execute(query, params)
    conn.commit()
    last_id = cursor.lastrowid
    cursor.close()
    return last_id


def execute_returning_id(conn, query: str, params: tuple = ()):
    """Execute INSERT and return the generated UUID by selecting UUID() first."""
    cursor = conn.cursor(dictionary=True)
    # Get a UUID from MySQL
    cursor.execute("SELECT UUID() AS id")
    row = cursor.fetchone()
    new_id = row["id"]
    cursor.close()
    # Execute the insert with the pre-generated UUID
    cursor2 = conn.cursor()
    cursor2.execute(query, (new_id, *params))
    conn.commit()
    cursor2.close()
    return new_id
