from functools import wraps
from .models import SlurpitSetting
from django.core.exceptions import ObjectDoesNotExist
from django.contrib import messages
from account.models import UserToken
from django.shortcuts import redirect

def slurpit_plugin_registered(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')

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
                
                appliance_type_param = request.GET.get('appliance_type', None)
                if appliance_type_param:
                    continue

                reset_param = request.GET.get('reset', None)
                if reset_param:
                    continue
                
                # tokens = UserToken.objects.filter(user=request.user).count()
                tokens = UserToken.objects.all().count()

                if tokens == 0:
                    messages.warning(request, "To use the Slurp'it plugin, it is necessary to first generate a Plugin API Key on the Setting Page.")
                    return view_func(request, *args, **kwargs)

                try:
                    setting = SlurpitSetting.objects.get()
                    server_url = setting.server_url
                    api_key = setting.api_key
                    appliance_type = setting.appliance_type

                    if appliance_type == '':
                        messages.warning(request, "To use the Slurp'it plugin, it is necessary to first select the Data synchronization Type on the Setting Page.")
                    elif appliance_type != 'push' and (api_key == '' or server_url == ''):
                        messages.warning(request, "To use the Slurp'it plugin, you should first configure the server settings. Go to settings and configure the Slurp'it server in the parameter section.")
                except Exception as e:
                    setting = None
                    messages.warning(request, "To use the Slurp'it plugin, it is necessary to first select the Data synchronization Type on the Setting Page.")

                return view_func(request, *args, **kwargs)

        return view_func(request, *args, **kwargs)
    return _wrapped_view