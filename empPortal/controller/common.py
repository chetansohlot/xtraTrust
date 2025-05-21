from django.http import JsonResponse
from empPortal.model import Referral
from empPortal.model import Partner
from django.conf import settings
from ..models import Users  
from django.contrib import messages
from empPortal.model.vehicleDetails import vehicleDetails
import os, requests, json
from ..utils import store_log
from django.forms.models import model_to_dict

def get_referrals(request):
    referrals = Referral.objects.filter(active=True).values('id', 'name')
    return JsonResponse(list(referrals), safe=False)

def get_posp(request):
    valid_user_ids = Users.objects.values_list('id', flat=True)
    partners = Partner.objects.filter(
        partner_status='4',  # 'Activated'
        user_id__in=valid_user_ids
    ).values('user_id', 'name')
    return JsonResponse(list(partners), safe=False)

def get_branch_sales_manager(request):
    branch_id = request.POST.get('branch_id')
    managers = Users.objects.filter(
        role_id='5',
        branch_id = branch_id,
        department_id = 1,
        is_active = True
    ).values('id', 'first_name','last_name')
    return JsonResponse(list(managers), safe=False)

def get_sales_team_leader(request):
    assigned_manager = request.POST.get('assigned_manager')
    branch_id = request.POST.get('branch_id')
    
    team_leaders = Users.objects.filter(
        branch_id = branch_id,
        senior_id = assigned_manager,
        department_id = 1,
        is_active = True
    ).values('id', 'first_name','last_name')
    return JsonResponse(list(team_leaders), safe=False)

def get_sales_relation_manager(request):
    assigned_teamleader = request.POST.get('assigned_teamleader')
    branch_id = request.POST.get('branch_id')
    
    relation_managers = Users.objects.filter(
        branch_id = branch_id,
        senior_id = assigned_teamleader,
        department_id = 1,
        is_active = True
    ).values('id', 'first_name','last_name')
    return JsonResponse(list(relation_managers), safe=False)

def fetch_vehicle_info(request): 
    if request.method == "POST":
        registration_number = request.POST.get("registration_number", "").strip()

        if not registration_number:
            return JsonResponse({"status": "error", "message": "Please enter a Registration number."}, status=400)

        vehicle_detail = vehicleDetails.objects.filter(registration_number=registration_number).first()

        if not vehicle_detail:
            vehicle_data = fetch_vehicle_details_from_api(registration_number)
            
            if vehicle_data:
                vehicle_detail = vehicleDetails.objects.create(
                    registration_number=registration_number,
                    vehicle_details=json.dumps(vehicle_data)
                )

                store_log(
                    log_type="INFO",
                    log_for="VAHAN_API",
                    message=f"Vahan API called for registration number {registration_number}",
                    user_id=request.user.id if request.user.is_authenticated else None,
                    ip_address=request.META.get("REMOTE_ADDR", "")
                )
        
        vehicle_json = {}
        if vehicle_detail and vehicle_detail.vehicle_details:
            try:
                vehicle_json = json.loads(vehicle_detail.vehicle_details)
            except json.JSONDecodeError:
                vehicle_json = {}

        return JsonResponse({
            "status": "success",
            "data": vehicle_json
        })

    return JsonResponse({"status": "error", "message": "Invalid request method."}, status=405)


def fetch_vehicle_details_from_api(registration_number):
    url = "https://live.zoop.one/api/v1/in/vehicle/rc/advance"
    ZOOP_APP_ID = os.getenv('ZOOP_APP_ID', "")
    ZOOP_API_KEY = os.getenv('ZOOP_API_KEY', "")

    headers = {
        "Content-Type": "application/json",
        "app-id": ZOOP_APP_ID,
        "api-key": ZOOP_API_KEY
    }
    data = {
        "mode": "sync",
        "data": {
            "vehicle_registration_number": registration_number,
            "consent": "Y",
            "consent_text": "I hereby declare my consent agreement for fetching my information via ZOOP API."
        }
    }
    
    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 200:
        return response.json()
    return None