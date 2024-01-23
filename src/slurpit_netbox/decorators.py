from functools import wraps
from .models import Setting
from django.core.exceptions import ObjectDoesNotExist
from django.contrib import messages

def slurpit_plugin_registered(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        
        paths = [
            'plugins/slurpit/settings/',
            'plugins/slurpit/devices/',
            'plugins/slurpit/data_mapping/',
            'plugins/slurpit/reconcile/',
            'plugins/slurpit/slurpitlog/'
        ]

        for path in paths:
            if path in request.path and request.method == 'GET':
                # Ignore test case
                test_param = request.GET.get('test',None)
                if test_param == 'test':
                    continue

                try:
                    setting = Setting.objects.get()
                    server_url = setting.server_url
                    api_key = setting.api_key
                    appliance_type = setting.appliance_type

                    if appliance_type == '':
                        messages.warning(request, "To use the Slurp'it plugin, you should need to choose Appliance Type at Setting Page.")
                    elif appliance_type != 'cloud' and api_key == '' or server_url == '':
                        messages.warning(request, "To use the Slurp'it plugin, you should first configure the server settings. Go to settings and configure the Slurp'it server in the parameter section.")
                except Exception as e:
                    setting = None
                    messages.warning(request, "To use the Slurp'it plugin, you should need to choose Appliance Type at Setting Page.")

                return view_func(request, *args, **kwargs)

        return view_func(request, *args, **kwargs)
    return _wrapped_view