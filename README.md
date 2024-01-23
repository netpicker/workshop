# Slurpit NetBox Plugin

It's assumed that we'll install NetBox in the local virtual environment.

## How to install the plugin on the NetBox

 ### Activate the Virtual Environment
 
 To ensure our plugin is accessible to the NetBox installation, we first need to activate the Python virtual environment that was created when we installed NetBox. To do this, determine the virtual environment's path (this will be /opt/NetBox/venv/ if you use the documentation's defaults) and activate it:

 ```
$ source /opt/NetBox/venv/bin/activate
 ```

 ### Run setup.py

 ```
$ python3 setup.py develop
 ```

 ### Configure NetBox
 
 Finally, we need to configure NetBox to enable our new plugin. Over in the NetBox installation path, open NetBox/NetBox/configuration.py and look for the PLUGINS parameter

 ```
# configuration.py
PLUGINS = [
    'slurpit_NetBox',
]
 ``` 

 

 ### Apply Migrations

 We can apply the migration file using the migrate management command:

```
python NetBox/manage.py migrate slurpit_NetBox
```

 Save the file and run the NetBox development server (if not already running):

 ```
$ python3 manage.py runserver
 ```
