import os


PLUGINS = ['slurpit_netbox']
PLUGINS_CONFIG = {
    'slurpit_netbox': {
        'API_ENDPOINT': os.environ.get('SLURPIT_API_ENDPOINT', 'http://localhost:8080'),
        'API_HEADERS': {
            'authorization': os.environ.get('SLURPIT_API_TOKEN'),
            'useragent': 'netbox/requests',
        },
    }
}

