from netbox.views import generic
from ..models import SlurpitLog
from ..tables import LoggingTable
from ..filtersets import LoggingFilterSet
from ..decorators import slurpit_plugin_registered
from django.utils.decorators import method_decorator


@method_decorator(slurpit_plugin_registered, name='dispatch')
class LoggingListView(generic.ObjectListView):
    queryset = SlurpitLog.objects.all().order_by("-log_time")
    filterset = LoggingFilterSet
    table = LoggingTable
    template_name = "slurpit_netbox/slurpitlog_list.html"