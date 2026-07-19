import json
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from .services.attendance_service import AttendanceService

@method_decorator(csrf_exempt, name='dispatch')
class RFIDScanView(View):
    """
    API Endpoint for RFID devices to push scan data.
    Expected POST payload (JSON):
    {
        "api_key": "device_api_key_here",
        "uid": "12345678"
    }
    """

    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            api_key = data.get("api_key")
            uid = data.get("uid")

            if not api_key or not uid:
                return JsonResponse(
                    {"success": False, "message": "Missing api_key or uid"}, status=400
                )

            result = AttendanceService.process_rfid_scan(api_key=api_key, uid=uid)
            status_code = 200 if result["success"] else 400
            return JsonResponse(result, status=status_code)

        except json.JSONDecodeError:
            return JsonResponse({"success": False, "message": "Invalid JSON"}, status=400)
        except Exception as e:
            return JsonResponse({"success": False, "message": str(e)}, status=500)
