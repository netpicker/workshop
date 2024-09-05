import pynetbox
import json
from reconcile import store_reconcile

# Initialize the pynetbox API connection
nb = pynetbox.api(
    'http://localhost:8000',
    token='028d32715cbe39df0c9409649026c1e20a80bdb5'
)

# Mapping for the device configuration
mapping_device = {
    "name": "",  # Required: Device name
    "device_type": None,  # Required: ID or slug of the device type
    "device_role": None,  # Required: ID or slug of the device role
    "site": None,  # Required: ID or slug of the site where the device is located

    # Optional: The tenant to which the device is assigned (ID or unique identifier)
    "tenant": None,

    # Optional: The platform (e.g., "cisco_ios", "juniper_junos")
    "platform": None,

    # Optional: Management IP address
    "primary_ip4": None,

    # Optional: Status of the device (e.g., "active", "staged", "decommissioned")
    "status": "active",

    # Optional: Free-text description of the device
    "description": "",

    # Optional: Dictionary of custom fields defined in your NetBox instance
    "custom_fields": {},

    # Optional: List of tags associated with the device
    "tags": []
}

# Reconcile Flag
reconcile = True

# Example devices to be added or updated
slurpit_devices = [
    {
        "name": "device1",
        "device_type": 1,  # You can replace with the ID or slug of the device type
        "device_role": 1,  # You can replace with the ID or slug of the device role
        "site": 1  # Replace with the site ID where the device is located
    },
    {
        "name": "device2",
        "device_type": 2,
        "device_role": 1,
        "site": 2
    }
]

def add_devices():
    try:
        """Adds Devices to NetBox."""
        create_queues = []
        for device in slurpit_devices:
            create_queues.append({
                **device, **mapping_device
            })

        # Bulk Create
        if reconcile:
            data = []
            for item in create_queues:
                data.append(('device', json.dumps(item)))

            if len(data):
                store_reconcile(data)

        else:
            nb.dcim.devices.create(create_queues)
    except Exception as e:
        print(f"Error adding devices: {e}")

def update_devices():
    """Updates existing devices in NetBox."""
    update_queues = []
    for new_device in slurpit_devices:
        try:
            # Retrieve the existing device by name
            device = nb.dcim.devices.get(name=new_device['name'])
            if device:
                # Prepare the update data
                update_data = {**new_device, "id": device.id}
                update_queues.append(update_data)
            else:
                print(f"No device found with name: {new_device['name']}")
        except Exception as e:
            print(f"Error fetching device {new_device['name']}: {e}")

    # Perform the update if there are any devices to update
    if update_queues:
        try:
            nb.dcim.devices.update(update_queues)
            print(f"Successfully updated devices: {[device['name'] for device in update_queues]}")
        except Exception as e:
            print(f"Error updating devices: {e}")

# Execute the functions
add_devices()
# update_devices()
