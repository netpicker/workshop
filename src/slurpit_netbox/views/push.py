from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from ..models import Setting, SlurpitLog
from ..validator import device_validator
from django.core.exceptions import ObjectDoesNotExist
from ..importer import process_import, import_devices
from ..management.choices import *
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from dcim.models import Device
import json


class PushDeviceView(APIView):
    
    permission_classes = [IsAuthenticated]
    queryset = Device.objects.all()
    
    def post(self, request):
        # Load JSON data from the request body
        devices = json.loads(request.body.decode('utf-8'))

        errors = device_validator(devices)

        if errors:
            return JsonResponse({'status': 'error', 'errors': errors}, status=400)

        import_devices(devices)
        process_import()

        return JsonResponse({'status': 'success'})