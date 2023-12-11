# Slurpit Netbox Plugin

We assume to install Netbox on your local virtual environment.
## How to install the plugin on the Netbox

 ### Activate the Virtual Environment
 
 To ensure our plugin is accessible to the NetBox installation, we first need to activate the Python virtual environment that was created when we installed NetBox. To do this, determine the virtual environment's path (this will be /opt/netbox/venv/ if you use the documentation's defaults) and activate it:

 ```
$ source /opt/netbox/venv/bin/activate
 ```

 ### Run setup.py

 ```
$ python3 setup.py develop
 ```

 ### Configure Netbox
 
 Finally, we need to configure NetBox to enable our new plugin. Over in the NetBox installation path, open netbox/netbox/configuration.py and look for the PLUGINS parameter

 ```
# configuration.py
PLUGINS = [
    'slurpit_netbox',
]
 ``` 

 And we need to set the API_ENDPOINT and API_HEADERS to integrate the Slurpit. eg: http://localhost as API_ENDPOINT

 ```
PLUGINS_CONFIG = {
        'slurpit_netbox':{
                'API_ENDPOINT': 'http://localhost', 
                'API_HEADERS': {
                        'authorization': YOUR_SLURPIT_API_KEY,
                        'useragent': 'netbox/requests',
                }
        }
}
 ```

 Save the file and run the Netbox development server (if not already running):

 ```
$ python3 manage.py runserver
 ```
