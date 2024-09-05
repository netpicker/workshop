import pynetbox
import json
from reconcile import store_reconcile

# Initialize the pynetbox API connection
nb = pynetbox.api(
    'http://localhost:8000',
    token='028d32715cbe39df0c9409649026c1e20a80bdb5'
)

# Static mapping for optional IPAM attributes in NetBox
mapping_ipams = {
    "status": "active",  # Required: The status of the IP address (e.g., "active", "reserved", etc.)

    # Optional: Free-text description of the IP address
    "description": "",

    # Optional: Role of the IP address (e.g., "loopback", "secondary", etc.)
    "role": "",

    # Optional: Tenant to which the IP address is assigned (ID or unique identifier)
    "tenant": None,

    # Optional: VRF instance associated with the IP address (ID or unique identifier)
    "vrf": None,

    # Optional: Type of object the IP address is assigned to (e.g., "dcim.interface")
    "assigned_object_type": "",

    # Optional: ID of the object to which the IP address is assigned
    "assigned_object_id": None,

    # Optional: ID of the "inside" IP address in a NAT mapping
    "nat_inside": None,

    # Optional: ID of the "outside" IP address in a NAT mapping
    "nat_outside": None,

    # Optional: List of tags associated with the IP address
    "tags": [],

    # Optional: Dictionary of custom fields defined in your NetBox instance
    "custom_fields": {}
}

# Reconcile Flag
reconcile = True

# List of IP addresses to add/update in NetBox
# Each entry must include the required fields: "address" and "dns_name"
# The fields from mapping_ipams can be optionally added to each entry as needed.
slurpit_ipams = [
    {
        "address": "192.168.10.10/24",  # Required: The IP address in CIDR notation
        "dns_name": "test2.com",        # Required: DNS name associated with the IP address
    },
    {
        "address": "192.168.10.20/24",  # Required: The IP address in CIDR notation
        "dns_name": "test2.com",        # Required: DNS name associated with the IP address
    }
]

def add_ipams():
    try:
        """Adds IP addresses to NetBox."""
        create_queues = []
        for ipam in slurpit_ipams:
            # Combine the provided IPAM data with optional mapping_ipams fields
            create_queues.append({
                **ipam, **mapping_ipams
            })

        # Bulk Create
        if reconcile:
            data = []
            for item in create_queues:
                data.append(('ipam', json.dumps(item)))
            
            if len(data):
                store_reconcile(data)

        else:
            nb.ipam.ip_addresses.create(create_queues)
    except:
        pass

def update_ipams():
    """Updates existing IP addresses in NetBox."""
    update_queues = []
    for ipam in slurpit_ipams:
        try:
            # Retrieve the existing IP object by address
            ip = nb.ipam.ip_addresses.get(address=ipam['address'])
            if ip:
                # Prepare the update data
                update_data = {**ipam, "id": ip.id}
                update_queues.append(update_data)
            else:
                print(f"No IP found with address: {ipam['address']}")
        except Exception as e:
            print(f"Error fetching IP {ipam['address']}: {e}")

    # Perform the update if there are any IPs to update
    if update_queues:
        try:
            nb.ipam.ip_addresses.update(update_queues)
            print(f"Successfully updated IPs: {[ipam['address'] for ipam in update_queues]}")
        except Exception as e:
            print(f"Error updating IPs: {e}")

# Execute the functions
add_ipams()
# update_ipams()
