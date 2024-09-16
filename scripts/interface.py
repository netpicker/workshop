import pynetbox
import json
from reconcile import store_reconcile

# Initialize the pynetbox API connection
nb = pynetbox.api(
    'http://localhost:8000',
    token='028d32715cbe39df0c9409649026c1e20a80bdb5'
)

mapping_interface = {
    "name": "",  # Required: The name of the interface (e.g., "GigabitEthernet0/1")

    # Optional: The device or virtual machine the interface is assigned to (ID or unique identifier)
    "device": None,

    # Optional: The type of interface (e.g., "1000Base-T", "10GBASE-SR", etc.)
    "type": "",

    # Optional: The MAC address of the interface
    "mac_address": "",

    # Optional: The description of the interface
    "description": "",

    # Optional: The enabled status of the interface (True/False)
    "enabled": True,

    # Optional: The MTU (Maximum Transmission Unit) size for the interface
    "mtu": None,

    # Optional: The mode of the interface (e.g., "access", "tagged", "tagged all", etc.)
    "mode": None,

    # Optional: The untagged VLAN ID associated with the interface (if mode is "access" or "tagged")
    "untagged_vlan": None,

    # Optional: List of tagged VLAN IDs associated with the interface (if mode is "tagged" or "tagged all")
    "tagged_vlans": [],

    # Optional: The ID of the parent interface (if this interface is a sub-interface)
    "parent": None,

    # Optional: The ID of the LAG (Link Aggregation Group) interface that this interface is part of
    "lag": None,

    # Optional: The interface's bandwidth in Mbps
    "speed": None,

    # Optional: The status of the interface (e.g., "connected", "planned", "decommissioning", etc.)
    "status": "active",

    # Optional: The ID of the site where this interface is located
    "site": None,

    # Optional: The tenant to which the interface is assigned (ID or unique identifier)
    "tenant": None,

    # Optional: List of tags associated with the interface
    "tags": [],

    # Optional: Dictionary of custom fields defined in your NetBox instance
    "custom_fields": {}
}


# Reconcile Flag
reconcile = True

slurpit_interfaces = [
    {
        "name": "interface1"
    },
    {
        "name": "interface2"
    }
]

def add_interfaces():
    try:
        """Adds Interfaces to NetBox."""
        create_queues = []
        for interface in slurpit_interfaces:
            create_queues.append({
                **interface, **mapping_interface
            })

        # Bulk Create
        if reconcile:
            data = []
            for item in create_queues:
                data.append(('interface', json.dumps(item)))
            
            if len(data):
                store_reconcile(data)

        else:
            nb.dcim.interfaces.create(create_queues)
    except:
        pass

def update_interfaces():
    """Updates existing Interfaces in NetBox."""
    update_queues = []
    for new_interface in slurpit_interfaces:
        try:
            # Retrieve the existing interface name
            interface = nb.dcim.interfaces.get(name=new_interface['name'])
            if interface:
                # Prepare the update data
                update_data = {**new_interface, "id": interface.id}
                update_queues.append(update_data)
            else:
                print(f"No Interface found with name: {new_interface['name']}")
        except Exception as e:
            print(f"Error fetching Interface {new_interface['name']}: {e}")

    # Perform the update if there are any Interfaces to update
    if update_queues:
        try:
            nb.dcim.interfaces.update(update_queues)
            print(f"Successfully updated Interfaces: {[interface['name'] for interface in update_queues]}")
        except Exception as e:
            print(f"Error updating Interfaces: {e}")

# Execute the functions
add_interfaces()
# update_interfaces()
