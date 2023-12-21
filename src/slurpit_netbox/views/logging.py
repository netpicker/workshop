from netbox.views import generic
from ..models import SlurpitLog
from ..tables import LoggingTable
from ..filtersets import LogginFilterSet

class LoggingListView(generic.ObjectListView):
    queryset = SlurpitLog.objects.all()
    filterset = LogginFilterSet
    table = LoggingTable
    template_name = "slurpit_netbox/slurpitlog_list.html"
