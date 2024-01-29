## Compatibility

| NetBox Version | Plugin Version |
|----------------|----------------|
|   NetBox 3.7   |    >= 0.8.0    |

## How to install the plugin on your local NetBox server

### Activate the Virtual Environment
 
Firstly, to make the plugin available within NetBox, we must activate the Python virtual environment that was set up during the NetBox installation; you can do this by finding the path of the virtual environment, which typically is /opt/netbox/venv/ if you followed the default installation guide.

 ```
$ source /opt/netbox/venv/bin/activate
 ```

 ### Run setup.py

 ```
$ python setup.py develop
 ```

 ### Configure NetBox
 
To enable our new plugin, we have to configure NetBox by opening the configuration.py file located in the netbox/netbox directory and modifying the PLUGINS parameter.

 ```
# configuration.py
PLUGINS = [
    'slurpit_netbox',
]
 ``` 

 

 ### Apply Migrations

Use the 'migrate' management command to apply the migration file.

```
python manage.py migrate slurpit_netbox
```

After saving the file, start the NetBox development server if it isn't already running.

 ```
$ python manage.py runserver 0.0.0.0:8000 --insecure
 ```
