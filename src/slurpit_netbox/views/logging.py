from netbox.views import generic
from ..models import SlurpitLog
from ..tables import LoggingTable
from ..filtersets import LoggingFilterSet
from ..decorators import slurpit_plugin_registered
from django.utils.decorators import method_decorator
from django.shortcuts import redirect
from ..management.choices import *

@method_decorator(slurpit_plugin_registered, name='dispatch')
class LoggingListView(generic.ObjectListView):
    queryset = SlurpitLog.objects.all().order_by("-log_time")
    filterset = LoggingFilterSet
    table = LoggingTable
    template_name = "slurpit_netbox/slurpitlog_list.html"
    
    def get(self, request, *args, **kwargs):        
        clear = request.GET.get('clear', None)

        if clear is not None:
            SlurpitLog.objects.all().delete()
            SlurpitLog.success(category=LogCategoryChoices.LOGGING, message=f'{request.user} cleared the logging')
            return redirect(request.path)
        
        return super().get(request, *args, **kwargs)