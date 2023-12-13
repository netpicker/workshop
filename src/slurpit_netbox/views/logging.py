from netbox.views import generic
from ..models import SlurpitLog
from ..tables import LoggingTable

class LoggingListView(generic.ObjectListView):
    queryset = SlurpitLog.objects.all()
    table = LoggingTable
    template_name = "slurpit_netbox/slurpitlog_list.html"
