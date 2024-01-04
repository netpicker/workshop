import uuid
import hashlib

def generate_random_string():
    # Generate a UUID and convert it to a string
    unique_id = str(uuid.uuid4())
    
    # Get the UTF-8 encoded bytes of the UUID string
    encoded_id = unique_id.encode('utf-8')

    # Create a SHA256 hash of the encoded UUID
    sha256_hash = hashlib.sha256(encoded_id)

    # Convert the SHA256 hash to a hexadecimal string
    hashed_string = sha256_hash.hexdigest()

    return hashed_string