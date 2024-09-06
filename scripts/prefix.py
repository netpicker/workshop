import pynetbox
import json
from reconcile import store_reconcile

# Initialize the pynetbox API connection
nb = pynetbox.api(
    'http://localhost:8000',
    token='028d32715cbe39df0c9409649026c1e20a80bdb5'
)

mapping_prefix = {
    "prefix": "",  # Required: The CIDR notation of the prefix (e.g., "192.168.1.0/24")

    # Optional: ID of the VRF (Virtual Routing and Forwarding) associated with the prefix
    "vrf": None,

    # Optional: The status of the prefix (e.g., "container", "active", "reserved", "deprecated")
    "status": "active",

    # Optional: The tenant to which the prefix is assigned (ID or unique identifier)
    "tenant": None,

    # Optional: ID of the site where this prefix is located
    "site": None,

    # Optional: The ID of the VLAN associated with the prefix
    "vlan": None,

    # Optional: The role of the prefix (e.g., "loopback", "secondary", etc.)
    "role": None,

    # Optional: Description of the prefix
    "description": "",

    # Optional: Boolean indicating if the prefix is marked as a pool for automatic IP allocation
    "is_pool": False,

    # Optional: Date the prefix was created (format: "YYYY-MM-DD")
    "date_created": None,

    # Optional: List of tags associated with the prefix
    "tags": [],

    # Optional: Dictionary of custom fields defined in your NetBox instance
    "custom_fields": {},

    # Optional: Boolean indicating if the prefix is a NAT (Network Address Translation) outside prefix
    "nat_outside": False
}

# Reconcile Flag
reconcile = True

slurpit_prefixes = [
    {
        "prefix": "192.168.5.5/32"
    },
    {
        "prefix": "192.168.10.0/24"
    }
]

def add_prefixes():
    try:
        """Adds Prefixes to NetBox."""
        create_queues = []
        for prefix in slurpit_prefixes:
            create_queues.append({
                **prefix, **mapping_prefix
            })

        # Bulk Create
        if reconcile:
            data = []
            for item in create_queues:
                data.append(('prefix', json.dumps(item)))
            
            if len(data):
                store_reconcile(data)

        else:
            nb.ipam.prefixes.create(create_queues)
    except:
        pass

def update_prefixes():
    """Updates existing Prefixes in NetBox."""
    update_queues = []
    for new_prefix in slurpit_prefixes:
        try:
            # Retrieve the existing perfix name
            prefix = nb.ipam.prefixes.get(prefix=new_prefix['prefix'])
            if prefix:
                # Prepare the update data
                update_data = {**new_prefix, "id": prefix.id}
                update_queues.append(update_data)
            else:
                print(f"No Perfix found with name: {new_prefix['prefix']}")
        except Exception as e:
            print(f"Error fetching Perfix {new_prefix['prefix']}: {e}")

    # Perform the update if there are any Perfixes to update
    if update_queues:
        try:
            nb.ipam.prefixes.update(update_queues)
            print(f"Successfully updated Prefixes: {[prefix['prefix'] for prefix in update_queues]}")
        except Exception as e:
            print(f"Error updating Prefixes: {e}")

# Execute the functions
add_prefixes()
# update_prefixes()
