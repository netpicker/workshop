import pynetbox
import json
from reconcile import store_reconcile

# Initialize the pynetbox API connection
nb = pynetbox.api(
    'http://localhost:8000',
    token='028d32715cbe39df0c9409649026c1e20a80bdb5'
)

mapping_vrf = {
    "name": "",  # Required: The name of the VRF (e.g., "Mgmt VRF")

    # Optional: The RD (Route Distinguisher) value (e.g., "100:1")
    "rd": None,

    # Optional: Description of the VRF
    "description": "",

    # Optional: The tenant to which the VRF is assigned (ID or unique identifier)
    "tenant": None,

    # Optional: The ID of the site where this VRF is located
    "site": None,

    # Optional: The ID of the role (e.g., "internal", "user", etc.)
    "role": None,

    # Optional: Free-text description of the VRF
    "description": "",

    # Optional: List of tags associated with the VRF
    "tags": [],

    # Optional: Dictionary of custom fields defined in your NetBox instance
    "custom_fields": {}
}

# Reconcile Flag
reconcile = True

slurpit_vrfs = [
    {
        "name": "vrf1",
        "rd": "100:1"
    },
    {
        "name": "vrf2",
        "rd": "200:1"
    }
]

def add_vrfs():
    try:
        """Adds VRFs to NetBox."""
        create_queues = []
        for vrf in slurpit_vrfs:
            create_queues.append({
                **vrf, **mapping_vrf
            })

        # Bulk Create
        if reconcile:
            data = []
            for item in create_queues:
                data.append(('vrf', json.dumps(item)))

            if len(data):
                store_reconcile(data)

        else:
            nb.ipam.vrfs.create(create_queues)
    except Exception as e:
        print(f"Error adding VRFs: {e}")

def update_vrfs():
    """Updates existing VRFs in NetBox."""
    update_queues = []
    for new_vrf in slurpit_vrfs:
        try:
            # Retrieve the existing VRF by name
            vrf = nb.ipam.vrfs.get(name=new_vrf['name'])
            if vrf:
                # Prepare the update data
                update_data = {**new_vrf, "id": vrf.id}
                update_queues.append(update_data)
            else:
                print(f"No VRF found with name: {new_vrf['name']}")
        except Exception as e:
            print(f"Error fetching VRF {new_vrf['name']}: {e}")

    # Perform the update if there are any VRFs to update
    if update_queues:
        try:
            nb.ipam.vrfs.update(update_queues)
            print(f"Successfully updated VRFs: {[vrf['name'] for vrf in update_queues]}")
        except Exception as e:
            print(f"Error updating VRFs: {e}")

# Execute the functions
add_vrfs()
# update_vrfs()
