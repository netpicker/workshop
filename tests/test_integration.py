import pytest
import psycopg2
import os

from datetime import datetime

def connection():
    return psycopg2.connect(
        dbname=os.environ.get("DB_NAME"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD"),
        host=os.environ.get("DB_HOST"),
        port=5432
    )

@pytest.fixture(scope="module")
def setup():
    with connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM auth_user WHERE username = %s", ("admin",))
        if cur.fetchone()[0] == 0:
            cur.execute("INSERT INTO auth_user (id, password, username, first_name, last_name, email, is_superuser, is_staff, is_active, date_joined ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", 
                (1, "pbkdf2_sha256$600000$gXgBKCHH0zV22o4Rx20Pcw$HDRkA9cQ8adWvn1Ihs2+ArGeEZyn0Njdgzs4XB3iJdQ=", "admin", "", "", "", True, True, True, datetime.now()))
            cur.execute("INSERT INTO users_token (key, write_enabled, user_id, created, description) VALUES (%s, %s, %s, %s, %s)", 
                ("0d8a4cd172ae30bff3293dd409d8e4f3416f6e18", True, 1, datetime.now(), ""))


def test_plannings(setup):
    print("test1")

def test_2(setup):
    print("test2")
