import pynetbox
import json
from reconcile import store_reconcile

# Initialize the pynetbox API connection
nb = pynetbox.api(
    'http://localhost:8000',
    token='028d32715cbe39df0c9409649026c1e20a80bdb5'
)

mapping_vlan = {
    "vid": None,  # Required: The VLAN ID (e.g., 10, 100, etc.)

    # Optional: The name of the VLAN (e.g., "Management VLAN")
    "name": "",

    # Optional: The status of the VLAN (e.g., "active", "reserved", "deprecated")
    "status": "active",

    # Optional: The tenant to which the VLAN is assigned (ID or unique identifier)
    "tenant": None,

    # Optional: The ID of the site where this VLAN is located
    "site": None,

    # Optional: The ID of the VLAN group this VLAN belongs to
    "group": None,

    # Optional: The role of the VLAN (e.g., "management", "user", etc.)
    "role": None,

    # Optional: Free-text description of the VLAN
    "description": "",

    # Optional: List of tags associated with the VLAN
    "tags": [],

    # Optional: Dictionary of custom fields defined in your NetBox instance
    "custom_fields": {}
}


# Reconcile Flag
reconcile = True

slurpit_vlans = [
    {
        "name": "vlan1",
        "vid": 1
    },
    {
        "name": "vlan2",
        "vid": 10
    }
]

def add_vlans():
    try:
        """Adds Vlans to NetBox."""
        create_queues = []
        for vlan in slurpit_vlans:
            create_queues.append({
                **vlan, **mapping_vlan
            })

        # Bulk Create
        if reconcile:
            data = []
            for item in create_queues:
                data.append(('vlan', json.dumps(item)))
            
            if len(data):
                store_reconcile(data)

        else:
            nb.ipam.vlans.create(create_queues)
    except:
        pass

def update_vlans():
    """Updates existing Vlans in NetBox."""
    update_queues = []
    for new_vlan in slurpit_vlans:
        try:
            # Retrieve the existing vlan name
            vlan = nb.ipam.vlans.get(name=new_vlan['vlan'])
            if vlan:
                # Prepare the update data
                update_data = {**new_vlan, "id": vlan.id}
                update_queues.append(update_data)
            else:
                print(f"No Vlan found with name: {new_vlan['name']}")
        except Exception as e:
            print(f"Error fetching Vlan {new_vlan['name']}: {e}")

    # Perform the update if there are any Vlans to update
    if update_queues:
        try:
            nb.ipam.vlans.update(update_queues)
            print(f"Successfully updated Vlans: {[vlan['name'] for vlan in update_queues]}")
        except Exception as e:
            print(f"Error updating Vlans: {e}")

# Execute the functions
add_vlans()
# update_vlans()
