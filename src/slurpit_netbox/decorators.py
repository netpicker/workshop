from functools import wraps
from .models import Setting
from django.core.exceptions import ObjectDoesNotExist
from django.contrib import messages

def slurpit_plugin_registered(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        print("Decorator two applied.")
        try:
            setting = Setting.objects.get()
            server_url = setting.server_url
            api_key = setting.api_key
            
            if api_key == '' or server_url == '':
                messages.warning(request, "To use the Slurp'it plugin you should first configure the server settings. Go to settings and configure the Slurp'it server in the parameter section.")
        except ObjectDoesNotExist:
            setting = None
            messages.warning(request, "To use the Slurp'it plugin you should first configure the server settings. Go to settings and configure the Slurp'it server in the parameter section.")
        return view_func(request, *args, **kwargs)
    return _wrapped_view