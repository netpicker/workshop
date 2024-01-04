import json
from datetime import datetime

def device_validator(data):
    # Perform your custom validation logic here.
    # For example, we check if required fields are present and have the correct format:
    required_fields = ['id', 'hostname', 'fqdn', 'device_os', 
                       'device_type', 'brand', 'disabled', 
                       'added', 'last_seen', 'createddate', 'changeddate']
    
    errors = []
    
    for entry in data:
        for field in required_fields:
            if field not in entry:
                errors.append(f"Missing {field} in entry with id {entry.get('id', 'unknown')}")
            else:
                # Further validation logic for each field could go here,
                # like checking that 'last_seen' is a valid datetime for instance:
                if field in ['last_seen', 'createddate', 'changeddate']:
                    try:
                        # Assuming the dates are in ISO format (YYYY-MM-DD HH:MM:SS)
                        datetime.strptime(entry[field], '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        errors.append(f"Invalid date format for {field} in entry with id {entry.get('id', 'unknown')}")

                if field == 'disabled' and entry[field] not in ['0', '1']:
                    errors.append(f"Invalid value for disabled in entry with id {entry.get('id', 'unknown')}")
    
    return errors