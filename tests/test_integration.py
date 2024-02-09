import pytest
import psycopg2
import os
import requests

from psycopg2.extras import DictCursor
from datetime import datetime

def connection():
    return psycopg2.connect(
        dbname=os.environ.get("DB_NAME"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD"),
        host=os.environ.get("DB_HOST"),
        port=5432,
        cursor_factory=DictCursor
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

def do_request(url, method="GET", data={}):
    #base_url = 'http://localhost:8080/api/plugins/slurpit'
    base_url = 'http://netbox:8080/api/plugins/slurpit'
    headers = {'Content-Type': 'application/json', 'Authorization': 'Token 0d8a4cd172ae30bff3293dd409d8e4f3416f6e18' }

    if method == "GET":
        return requests.get(f'{base_url}/{url}', headers=headers)
    if method == "DELETE":
        return requests.delete(f'{base_url}/{url}', headers=headers)
    if method == "POST":
        return requests.post(f'{base_url}/{url}', headers=headers, json=data)

def get_plannings():
    with connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM slurpit_netbox_slurpitplanning")
        return cur.fetchall()

def compare_plannings(array1, array2):
    assert len(array1) == len(array2), f"Planning arrays were different sizes: {array1} - {array2}"

    for row in array1:
        result = next((obj for obj in array2 if obj['planning_id'] == row['id']), None)
        assert result is not None, f"Unable to find planning_id {row['id']}"
        assert row['name'] == result['name']
        assert row['comment'] == result['comments']

def test_plannings(setup):
    insert_plannings = [{
        'id':5,
        'name': 'test',
        'comment': 'asd',
        'disabled': '0'
    }]
    response = do_request('planning/', method="POST",data=insert_plannings)
    assert response.status_code == 200
    assert response.json()['status'] == "success"

    compare_plannings(insert_plannings, get_plannings())
    
    update_plannings = [{
        'id':5,
        'name': 'test updated',
        'comment': 'asd updated',
        'disabled': '0'
    }]
    response = do_request('planning/', method="POST",data=update_plannings)
    assert response.status_code == 200
    assert response.json()['status'] == "success"

    compare_plannings(update_plannings, get_plannings())
    
    sync_plannings = [{
        'id':6,
        'name': 'new test',
        'comment': 'new asd',
        'disabled': '0'
    }]
    response = do_request('planning/sync/', method="POST",data=sync_plannings)
    assert response.status_code == 200
    assert response.json()['status'] == "success"

    compare_plannings(sync_plannings, get_plannings())
    
    disable_plannings = [{
        'id':6,
        'name': 'new test',
        'comment': 'new asd',
        'disabled': '1'
    }]
    response = do_request('planning/sync/', method="POST",data=disable_plannings)
    assert response.status_code == 200
    assert response.json()['status'] == "success"

    assert len(get_plannings()) == 0

