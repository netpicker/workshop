import pytest
import psycopg2
import os
import requests

from psycopg2.extras import DictCursor, NamedTupleCursor
from datetime import datetime
import json

# from dotenv import load_dotenv
# # Load the .env file
# load_dotenv()

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
        cur.execute("SELECT COUNT(*) FROM users_user WHERE username = %s", ("admin",))
        if cur.fetchone()[0] == 0:
            cur.execute("INSERT INTO users_user (id, password, username, first_name, last_name, email, is_superuser, is_staff, is_active, date_joined ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", 
                (1, "pbkdf2_sha256$600000$gXgBKCHH0zV22o4Rx20Pcw$HDRkA9cQ8adWvn1Ihs2+ArGeEZyn0Njdgzs4XB3iJdQ=", "admin", "", "", "", True, True, True, datetime.now()))
            cur.execute("INSERT INTO users_token (key, write_enabled, user_id, created, description) VALUES (%s, %s, %s, %s, %s)", 
                ("0d8a4cd172ae30bff3293dd409d8e4f3416f6e18", True, 1, datetime.now(), ""))
headers = {
    'Content-Type': 'application/json', 
    'Authorization': 'Token 0d8a4cd172ae30bff3293dd409d8e4f3416f6e18',
}
def do_request(url, method="GET", data={}, base_url = 'http://netbox:8080/api/plugins/slurpit'):
    # base_url = 'http://netbox:8080/api/plugins/slurpit'
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
    # assert len(array1) == len(array2), f"Planning arrays were different sizes: {array1} - {array2}"

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
    assert response.status_code == 200, f"Status wasnt 200 \n{response.text}"
    assert response.json()['status'] == "success"

    compare_plannings(insert_plannings, get_plannings())
    
    update_plannings = [{
        'id':5,
        'name': 'test updated',
        'comment': 'asd updated',
        'disabled': '0'
    }]
    response = do_request('planning/', method="POST",data=update_plannings)
    assert response.status_code == 200, f"Status wasnt 200 \n{response.text}"
    assert response.json()['status'] == "success"

    compare_plannings(update_plannings, get_plannings())
    
    sync_plannings = [{
        'id':6,
        'name': 'new test',
        'comment': 'new asd',
        'disabled': '0'
    }]
    response = do_request('planning/sync/', method="POST",data=sync_plannings)
    assert response.status_code == 200, f"Status wasnt 200 \n{response.text}"
    assert response.json()['status'] == "success"

    compare_plannings(sync_plannings, get_plannings())
    
    disable_plannings = [{
        'id':6,
        'name': 'new test',
        'comment': 'new asd',
        'disabled': '1'
    }]
    response = do_request('planning/sync/', method="POST",data=disable_plannings)
    assert response.status_code == 200, f"Status wasnt 200 \n{response.text}"
    assert response.json()['status'] == "success"

    assert len(get_plannings()) == 0


def compare_devices(array1, array2):
    assert len(array1) == len(array2), f"Device arrays were different sizes: {array1} - {array2}"
    
    for row in array1:
        result = next((obj for obj in array2 if obj['slurpit_id'] == row['id']), None)
        assert result is not None, f"Unable to find slurpit_id {row['id']}"
        assert row['hostname'] == result['hostname']
        assert row['fqdn'] == result['fqdn']
        assert row['device_os'] == result['device_os']
        assert row['device_type'] == result['device_type']
        assert row['brand'] == result['brand']
        assert row['ipv4'] == result['ipv4']

def get_devices():
    with connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM slurpit_netbox_slurpitstageddevice")
        return cur.fetchall()

def test_devices(setup):
    devices = [{
        "id": 100,
        "hostname": "slurpit",
        "fqdn": "slurpit",
        "ipv4": "192.168.100.100",
        "device_os": "slurpit",
        "device_type": "slurpit",
        "brand": "slurpit",
        "disabled": "0",
        "createddate": "2023-11-27 14:05:26",
        "changeddate": "2024-04-04 16:27:23"
    }]
    response = do_request('device/', method="POST",data=devices)
    assert response.status_code == 200, f"Status wasnt 200 \n{response.text}"
    assert response.json()['status'] == "success"

    compare_devices(devices, get_devices())

    response = do_request('device/sync_start/', method="POST")
    assert response.status_code == 200, f"Status wasnt 200 \n{response.text}"
    assert response.json()['status'] == "success"

    response = do_request('device/sync/', method="POST", data=devices)
    assert response.status_code == 200, f"Status wasnt 200 \n{response.text}"
    assert response.json()['status'] == "success"


    response = do_request('device/sync_end/', method="POST")
    assert response.status_code == 200, f"Status wasnt 200 \n{response.text}"
    assert response.json()['status'] == "success"

    compare_devices(devices, get_devices())
    # Check if Platform & Manufacturer & Device Type are all created on slurpit.
    check_onboard_device(devices[0])

def check_onboard_device(device):
    with connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM slurpit_netbox_slurpitimporteddevice WHERE hostname=%s",
            (device['hostname'],)
        )
        imported_device =  cur.fetchone()

        assert imported_device != None, f'Imported device does not exist.'
        
        cur.execute(
            "SELECT * FROM dcim_devicetype WHERE model=%s",
            ('slurpit',)
        )
        devicetype =  cur.fetchone()
        assert devicetype != None, f'Slurpit Device Type does not exist.'

        cur.execute(
            "SELECT * FROM dcim_devicerole WHERE name=%s",
            ("Slurp'it",)
        )
        devicerole =  cur.fetchone()
        assert devicerole != None, f'Slurpit Device Role does not exist.'
        
        cur.execute(
            "SELECT * FROM dcim_site WHERE name=%s",
            ("Slurp'it",)
        )
        devicesite =  cur.fetchone()
        assert devicesite != None, f'Slurpit Site does not exist.'

        # do_request('onboard', 'POST', {
        #     'pk': imported_device['id'],
        #     'device_type': devicetype['id'],
        #     'site': devicesite['id'],
        #     'role': devicerole['id'],
        #     'csrfmiddlewaretoken': 'cfa4959977213da6419bc40c12c84d292419dc32',
        #     '_apply': ''
        # }, 'http://localhost:8000/plugins/slurpit/devices')

def set_reconcile(is_enable):
    with connection() as conn, conn.cursor() as cur:

        cur.execute(
            'UPDATE slurpit_netbox_slurpitinitipaddress SET enable_reconcile = %s, role = %s WHERE address IS NULL',
            (is_enable, "")
        )
        print(cur.rowcount)
        conn.commit()
        # Not Existed Case
        if cur.rowcount == 0:
            cur.execute(
                'INSERT INTO slurpit_netbox_slurpitinitipaddress (status, enable_reconcile, custom_field_data, description, comments, role) VALUES (%s, %s, %s, %s, %s, %s)',
                ("active", is_enable, json.dumps({}), "", "", "")
            )
            conn.commit()
        return cur.rowcount
    
def set_reconcile_for_interface(is_enable):
    with connection() as conn, conn.cursor() as cur:

        cur.execute(
            'UPDATE slurpit_netbox_slurpitinterface SET enable_reconcile = %s WHERE name = %s',
            (is_enable, "")
        )
        conn.commit()
        # Not Existed Case
        if cur.rowcount == 0:
            cur.execute(
                'INSERT INTO slurpit_netbox_slurpitinterface (type, enable_reconcile, custom_field_data, cable_end, mark_connected, enabled, mode, name, label, description, _name) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
                ("bridge", is_enable, json.dumps({}), '', False, False, '', '', '', '', '')
            )
            conn.commit()
        return cur.rowcount

def set_reconcile_for_prefix(is_enable):
    with connection() as conn, conn.cursor() as cur:

        cur.execute(
            'UPDATE slurpit_netbox_slurpitprefix SET enable_reconcile = %s WHERE prefix IS NULL',
            (is_enable, )
        )
        conn.commit()
        # Not Existed Case
        if cur.rowcount == 0:
            cur.execute(
                'INSERT INTO slurpit_netbox_slurpitprefix (status, enable_reconcile, custom_field_data, description, comments, is_pool, mark_utilized, _depth, _children) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)',
                ("active", is_enable, json.dumps({}), '', '', False, False, 0, 0)
            )
            conn.commit()
        return cur.rowcount
    
    
def check_direct_sync_ipam(ipams):
    with connection() as conn, conn.cursor() as cur:
        for ipam in ipams:
            cur.execute('SELECT * FROM ipam_ipaddress WHERE address=%s', (str(ipam['address']),)) 
            cnt = len(cur.fetchall())
            assert cnt > 0, f'{ipam["address"]} does not exist in NetBox.'

def check_reconcile_sync_ipam(ipams):
    with connection() as conn, conn.cursor() as cur:
        for ipam in ipams:
            cur.execute('SELECT * FROM slurpit_netbox_slurpitinitipaddress WHERE address=%s', (str(ipam['address']),)) 
            cnt = len(cur.fetchall())
            assert cnt > 0, f'{ipam["address"]} does not exist in Reconcile Table.'

def check_direct_sync_interface(interfaces):
    with connection() as conn, conn.cursor() as cur:
        for interface in interfaces:
            cur.execute('SELECT * FROM dcim_interface WHERE name=%s', (str(interface['name']),)) 
            cnt = len(cur.fetchall())
            assert cnt > 0, f'{interface["name"]} does not exist in NetBox.'

def check_direct_sync_prefix(prefixes):
    with connection() as conn, conn.cursor() as cur:
        for prefix in prefixes:
            cur.execute('SELECT * FROM ipam_prefix WHERE prefix=%s', (str(prefix['prefix']),)) 
            cnt = len(cur.fetchall())
            assert cnt > 0, f'{prefix["prefix"]} does not exist in NetBox.'

def check_reconcile_sync_prefix(prefixes):
    with connection() as conn, conn.cursor() as cur:
        for prefix in prefixes:
            cur.execute('SELECT * FROM slurpit_netbox_slurpitprefix WHERE prefix=%s', (str(prefix['prefix']),)) 
            cnt = len(cur.fetchall())
            assert cnt > 0, f'{prefix["prefix"]} does not exist in Reconcile Table.'


def check_reconcile_sync_interface(interfaces):
    with connection() as conn, conn.cursor() as cur:
        for interface in interfaces:
            cur.execute('SELECT * FROM slurpit_netbox_slurpitinterface WHERE name=%s', (str(interface['name']),)) 
            cnt = len(cur.fetchall())
            assert cnt > 0, f'{interface["name"]} does not exist in Reconcile Table.'

def test_ipams(setup):
    #IPAM Direct Sync Test
    #Set Enable to reconcile every incoming IPAM data
    set_reconcile(False)
    invalid_ipams = [
        {
            'address': '192.168.100.100/300',
            'status': 'active',
            'dns_name': 'test.com'
        }
    ]
    response = do_request('ipam/', method="POST", data=invalid_ipams)
    assert response.status_code == 400, f"Validation is Failed. Status wasnt 400 \n{response.json()}"

    valid_ipams = [
        {
            'address': '192.168.100.100/24',
            'status': 'active',
            'dns_name': 'test.com'
        }
    ]
    response = do_request('ipam/', method="POST", data=valid_ipams)
    assert response.status_code == 200, f"IPAM import is Failed. Status wasnt 200 \n{response.json()}"

    check_direct_sync_ipam(valid_ipams)

    #IPAM Reconcile Test
    set_reconcile(True)
    valid_ipams = [
        {
            'address': '192.168.200.200/24',
            'status': 'active',
            'dns_name': 'test.com',
            'description': 'Test'
        }
    ]
    response = do_request('ipam/', method="POST", data=valid_ipams)
    assert response.status_code == 200, f"IPAM import is Failed. Status wasnt 200 \n{response.json()}"

    check_reconcile_sync_ipam(valid_ipams)

def get_planning_from_id(id):
    with connection() as conn, conn.cursor() as cur:
        cur = conn.cursor(cursor_factory=NamedTupleCursor)
        cur.execute("SELECT * FROM slurpit_netbox_slurpitplanning WHERE planning_id=%s", (id,))
        return cur.fetchone()

def compare_snapshots(content, device_name, planning_id):
    with connection() as conn, conn.cursor() as cur:
        cur = conn.cursor(cursor_factory=NamedTupleCursor)
        cur.execute("SELECT * FROM slurpit_netbox_slurpitsnapshot WHERE hostname=%s and planning_id=%s and result_type='planning_result'", (device_name,planning_id))
        planning_result = cur.fetchone()
        assert planning_result != None, "Imported Planning result is not exsited"
        assert planning_result.content == content, "Imported Planning result is different with Original Data"
    pass

def test_planning_snapshots(setup):
    # Add Planning for test
    sync_plannings = [{
        'id':10,
        'name': 'slurpit',
        'comment': 'slurpit',
        'disabled': '0'
    }]
    response = do_request('planning/sync/', method="POST",data=sync_plannings)
    assert response.status_code == 200, f"Status wasnt 200 \n{response.text}"
    assert response.json()['status'] == "success"

    compare_plannings(sync_plannings, get_plannings())
    
    snapshots = {
        'slurpit': {
            'planning_id': '10',
            'batch_id': 3,
            'columns': [
                'name',
                'role'
            ],
            'planning_results': [
                {
                    'name': 'slurpit',
                    'role': 'slurpit'
                }
            ],
            'template_results': [
                {
                    'index': '14',
                    'name': 'slurpit'
                }
            ]
        }
    }
    content = {
                    'name': 'slurpit',
                    'role': 'slurpit'
                }
    response = do_request('planning-data/', method="POST",data=[{
        'hostname': 'slurpit',
        'planning_id': '10',
        'content': {'planning_result': content, 'template_result': ''},
        'result_type': 'planning_result'
    }])
    assert response.status_code == 200, f"Status wasnt 200 \n{response.text}"
    assert response.json()['status'] == "success"

    compare_snapshots(content, 'slurpit', 10)

def compare_mapping_fields():

    default_initial_items = ['device_os', 'device_type', 'fqdn', 'hostname', 'ipv4']
    with connection() as conn, conn.cursor() as cur:
        cur.execute('SELECT * FROM slurpit_netbox_slurpitmapping') 
        items = cur.fetchall()
        items = [item['source_field'] for item in items]
        items.sort()
        assert items == default_initial_items

def test_data_mapping(setup):
    # Test Initial Mapping Fields
    compare_mapping_fields()

def add_device_to_netbox():
    with connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM dcim_site WHERE name=%s", ("Slurp'it",))
        temp = cur.fetchone()
        site = temp['id']

        cur.execute("SELECT * FROM dcim_devicerole WHERE name=%s", ("Slurp'it",))
        temp = cur.fetchone()
        devicerole = temp['id']

        cur.execute("SELECT * FROM dcim_devicetype WHERE model=%s",("Slurp'it",))
        temp = cur.fetchone()
        devicetype = temp['id']

        cur.execute(
                'INSERT INTO dcim_device (device_type_id, site_id, role_id, status, name, custom_field_data, serial, face, comments, airflow, description, inventory_item_count, console_port_count, console_server_port_count, device_bay_count, power_port_count, power_outlet_count, interface_count, rear_port_count, front_port_count, module_bay_count) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
                (devicetype, site, devicerole, "active", "Slurp'it", json.dumps({}), "test", "test", "test", "test", "test", 1, 1, 1, 1, 1, 1, 1, 1, 1, 1)
            )
        conn.commit()
    pass

def test_interface(setup):
    #Interface Direct Sync Test
    #Set Enable to reconcile every incoming Interface data
    set_reconcile_for_interface(False)
    invalid_interfaces = [
        {
            'description': 'slurpit',
            'label': 'slurpit'
        }
    ]
    response = do_request('interface/', method="POST", data=invalid_interfaces)
    assert response.status_code == 400, f"Validation is Failed. Status wasnt 400 \n{response.json()}"

    add_device_to_netbox()

    valid_interfaces = [
        {
            'name': 'slurpit',
            'description': 'slurpit',
            'label': 'slurpit',
            'hostname': "Slurp'it"
        }
    ]
    response = do_request('interface/', method="POST", data=valid_interfaces)
    assert response.status_code == 200, f"Interfacce import is Failed. Status wasnt 200 \n{response.json()}"

    check_direct_sync_interface(valid_interfaces)

    #Interface Reconcile Test
    set_reconcile_for_interface(True)
    valid_interfaces = [
        {
            'name': 'slurpitTest',
            'description': 'slurpit',
            'label': 'slurpit',
            'hostname': "Slurp'it"
        }
    ]
    response = do_request('interface/', method="POST", data=valid_interfaces)
    assert response.status_code == 200, f"Interface import is Failed. Status wasnt 200 \n{response.json()}"

    check_reconcile_sync_interface(valid_interfaces)

def test_prefix(setup):
    #Prefix Direct Sync Test
    #Set Enable to reconcile every incoming Prefix data
    set_reconcile_for_prefix(False)
    invalid_prefixes = [
        {
            'prefix': '192.168.10.10',
        }
    ]
    response = do_request('prefix/', method="POST", data=invalid_prefixes)
    assert response.status_code == 400, f"Validation is Failed. Status wasnt 400 \n{response.json()}"

    valid_prefixes = [
        {
            'prefix': '192.168.100.100/32',
        }
    ]
    response = do_request('prefix/', method="POST", data=valid_prefixes)
    assert response.status_code == 200, f"Prefix import is Failed. Status wasnt 200 \n{response.json()}"

    check_direct_sync_prefix(valid_prefixes)

     #Prefix Reconcile Test
    set_reconcile_for_prefix(True)
    valid_prefixes = [
        {
            'prefix': '192.168.100.50/32',
        }
    ]
    response = do_request('prefix/', method="POST", data=valid_prefixes)
    assert response.status_code == 200, f"Prefix import is Failed. Status wasnt 200 \n{response.json()}"
    check_reconcile_sync_prefix(valid_prefixes)