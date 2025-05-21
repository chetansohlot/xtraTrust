from django.shortcuts import render,redirect, get_object_or_404
from ..models import Commission, Users, QuotationCustomer, VehicleInfo, QuotationVehicleDetail, QuotationFormData

from empPortal.model import Quotation

from django.db.models import OuterRef, Subquery
from django.contrib import messages
from datetime import datetime
from django.urls import reverse
import pprint  # Import pprint for better formatting
from django.http import JsonResponse
import pdfkit
import os
from django.conf import settings
from dotenv import load_dotenv
from django.templatetags.static import static  # ✅ Import static
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.forms.models import model_to_dict
import json
from datetime import date
import requests
from ..utils import store_log, create_or_update_lead
from django.core.mail import EmailMessage
import logging

logger = logging.getLogger(__name__)



def dictfetchall(cursor):
    "Returns all rows from a cursor as a dict"
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

def index(request):
    if not request.user.is_authenticated:
        return redirect('login')

    # Get filters from request
    customer_id = request.GET.get('customer_id', '').strip()
    customer_name = request.GET.get('customer_name', '').strip()
    customer_mobile = request.GET.get('customer_mobile', '').strip()
    policy_type = request.GET.get('policy_type', '').strip()
    quote_status = request.GET.get('quote_status', '').strip()
    quote_date_range = request.GET.get('quote_date_range', '').strip()
    vehicle_type = request.GET.get('vehicle_type', '').strip()
    ncb = request.GET.get('ncb', '').strip()
    insurer_name = request.GET.get('insurer_name', '').strip()

    
    # Get customer_ids from Quotation based on user role
    if request.user.role_id == 1:
        # Admin or superuser: show all quotations
        customer_ids = Quotation.objects.values_list('customer_id', flat=True)
    else:
        role_id = request.user.role_id
        user_id = request.user.id

        if role_id == 5:  # Manager
            team_leaders = Users.objects.filter(role_id=6, senior_id=user_id)
            relationship_managers = Users.objects.filter(role_id=7, senior_id__in=team_leaders.values_list('id', flat=True))
            user_ids = list(team_leaders.values_list('id', flat=True)) + \
                    list(relationship_managers.values_list('id', flat=True)) 
            customer_ids = Quotation.objects.filter(
                created_by__in=user_ids
            ).values_list('customer_id', flat=True)

        elif role_id == 6:  # Team Leader
            relationship_managers = Users.objects.filter(role_id=7, senior_id=user_id)
            user_ids = list(relationship_managers.values_list('id', flat=True))
            # Only show quotations created by the logged-in user
            customer_ids = Quotation.objects.filter(
                created_by__in=user_ids
            ).values_list('customer_id', flat=True)
        elif role_id == 7:  # Relationship Manager
            customer_ids = Quotation.objects.filter(
                created_by=str(request.user.id)
            ).values_list('customer_id', flat=True)

    # Base QuerySet, filtered by role
    quotations = QuotationCustomer.objects.filter(customer_id__in=customer_ids)

    # Apply filters dynamically
    if customer_id:
        quotations = quotations.filter(customer_id=customer_id)
    if customer_name:
        quotations = quotations.filter(name_as_per_pan__icontains=customer_name)
    if customer_mobile:
        quotations = quotations.filter(mobile_number__icontains=customer_mobile)
    # if policy_type:
        # quotations = quotations.filter(vehicleinfo__policy_type__icontains=policy_type)
    if quote_date_range:
        try:
            start_date, end_date = map(str.strip, quote_date_range.split(" - "))
            start_date = datetime.strptime(start_date, "%Y-%m-%d")
            end_date = datetime.strptime(end_date, "%Y-%m-%d")
            quotations = quotations.filter(created_at__range=[start_date, end_date])
        except ValueError:
            pass  # Ignore invalid date format
    # if vehicle_type:
    #     quotations = quotations.filter(vehicleinfo__vehicle_type__icontains=vehicle_type)
    # if ncb:
    #     try:
    #         ncb_value = float(ncb)
    #         quotations = quotations.filter(vehicleinfo__ncb_percentage=ncb_value)
    #     except ValueError:
    #         pass  # Ignore invalid ncb format
    # if insurer_name:
    #     quotations = quotations.filter(vehicleinfo__insurance_company__icontains=insurer_name)

    # Fetch latest vehicle information
    latest_vehicle_info = VehicleInfo.objects.filter(
        customer_id=OuterRef('customer_id')
    ).order_by('-created_at')

    # Annotate vehicle information
    quotations_with_vehicle = quotations.annotate(
        registration_number=Subquery(latest_vehicle_info.values('registration_number')[:1]),
        vehicle_type=Subquery(latest_vehicle_info.values('vehicle_type')[:1]),
        make=Subquery(latest_vehicle_info.values('make')[:1]),
        model=Subquery(latest_vehicle_info.values('model')[:1]),
        year_of_manufacture=Subquery(latest_vehicle_info.values('year_of_manufacture')[:1]),
        policy_type=Subquery(latest_vehicle_info.values('policy_type')[:1]),
        idv_value=Subquery(latest_vehicle_info.values('idv_value')[:1]),
        claim_history=Subquery(latest_vehicle_info.values('claim_history')[:1]),
        ncb_percentage=Subquery(latest_vehicle_info.values('ncb_percentage')[:1]),
        addons=Subquery(latest_vehicle_info.values('addons')[:1]),
        insurance_company=Subquery(latest_vehicle_info.values('insurance_company')[:1]),
    )

    # Calculate counters
    total_quotes = quotations_with_vehicle.count()

    # Add-ons Mapping
    ADDONS_MAP = {
        "1": "Zero Depreciation",
        "2": "Roadside Assistance",
        "3": "Engine Protection"
    }

    # Convert QuerySet to structured JSON response
    data = []
    for quotation in quotations_with_vehicle:
        customer_data = {field.name: getattr(quotation, field.name) for field in QuotationCustomer._meta.fields}
        vehicle_data = {
            "registration_number": quotation.registration_number,
            "vehicle_type": quotation.vehicle_type,
            "make": quotation.make,
            "model": quotation.model,
            "year_of_manufacture": quotation.year_of_manufacture,
            "policy_type": quotation.policy_type,
            "idv_value": quotation.idv_value,
            "claim_history": quotation.claim_history,
            "ncb_percentage": quotation.ncb_percentage,
            "addons": quotation.addons,
            "insurance_company": quotation.insurance_company,
        }

        customer_data['vehicle'] = vehicle_data if quotation.registration_number else {}
        customer_data['vehicle']['premium'] = "N/A"  # Placeholder, update with actual logic if available

        if customer_data["vehicle"].get("addons"):
            addons_key = str(customer_data["vehicle"]["addons"])
            customer_data["vehicle"]["addons_display"] = ADDONS_MAP.get(addons_key, "N/A")
        else:
            customer_data["vehicle"]["addons_display"] = "N/A"

        data.append(customer_data)

    context = {
        'quotations': data,
        'total_quotes': total_quotes,
    }

    return render(request, 'quote-management/index.html', context)



def fetch_customer(request):
    if request.method == "POST":
        mobile_number = request.POST.get("mobile_number", "").strip()

        if not mobile_number:
            messages.error(request, "Please enter a mobile number.")
            return redirect("quote-management-create")

        # Check if customer exists
        quotation = QuotationCustomer.objects.filter(mobile_number=mobile_number).first()

        if quotation:
            messages.success(request, f"Existing customer found! Customer ID: {quotation.customer_id}")
            return redirect(reverse("quote-management-edit", args=[quotation.customer_id]))
        else:
            # Generate new customer_id
            last_customer = QuotationCustomer.objects.order_by('-id').first()
            if last_customer and last_customer.customer_id.startswith("CUS"):
                last_number = int(last_customer.customer_id[3:])
                new_customer_id = f"CUS{last_number + 1}"
            else:
                new_customer_id = "CUS1000001"

            # Create a new customer record
            new_quotation = QuotationCustomer.objects.create(
                customer_id=new_customer_id,
                mobile_number=mobile_number,
                active=True,
            )

            messages.success(request, f"New customer created! Customer ID: {new_customer_id}")

            return redirect(reverse("quote-management-edit", args=[new_customer_id]))

    return redirect("quote-management-create")


def create_or_edit(request, customer_id=None):
    if not request.user.is_authenticated:
        return redirect('login')

    # Fetch existing customer if editing
    quotation = None
    if customer_id:
        quotation = get_object_or_404(QuotationCustomer, customer_id=customer_id)

    if request.method == "GET":
        products = [
            {'id': 1, 'name': 'Motor'},
            {'id': 2, 'name': 'Health'},
            {'id': 3, 'name': 'Term'},
        ]
        
        if request.user.role_id == 1:
            members = Users.objects.filter(role_id=2, activation_status='1')
        else:
            members = Users.objects.none()
        today = date.today()
        return render(request, 'quote-management/create.html', {
            'products': products,
            'members': members,
            'today': today,
            'quotation': quotation  # Pass existing data if editing
        })
    
    elif request.method == "POST":
        # Extract form data
        mobile_number = request.POST.get("mobile_number", "").strip()
        email_address = request.POST.get("email_address", "").strip()
        quote_date = request.POST.get("quote_date", "").strip()
        name_as_per_pan = request.POST.get("name_as_per_pan", "").strip()
        pan_card_number = request.POST.get("pan_card_number", "").strip() or None
        date_of_birth = request.POST.get("date_of_birth", "").strip()
        state = request.POST.get("state", "").strip()
        city = request.POST.get("city", "").strip()
        pincode = request.POST.get("pincode", "").strip()
        address = request.POST.get("address", "").strip()

        # Validate and format date fields
        try:
            quote_date = datetime.strptime(quote_date, "%Y-%m-%d").date() if quote_date else None
            date_of_birth = datetime.strptime(date_of_birth, "%Y-%m-%d").date() if date_of_birth else None
        except ValueError:
            messages.error(request, "Invalid date format.")
            return redirect(reverse("quote-management-create") if not customer_id else reverse("quote-management-edit", args=[customer_id]))

        if quotation:
            # Update existing record
            quotation.mobile_number = mobile_number
            quotation.email_address = email_address
            quotation.quote_date = quote_date
            quotation.name_as_per_pan = name_as_per_pan
            quotation.pan_card_number = pan_card_number
            quotation.date_of_birth = date_of_birth
            quotation.state = state
            quotation.city = city
            quotation.pincode = pincode
            quotation.address = address
            quotation.save()

            messages.success(request, f"Quotation updated successfully! Customer ID: {quotation.customer_id}")
            create_quotation(request, quotation.customer_id)
            # Redirect to vehicle info page
            return redirect(reverse("create-vehicle-info", args=[quotation.customer_id]))
        
        else:
            # Generate new customer_id
            last_customer = QuotationCustomer.objects.order_by('-id').first()
            if last_customer and last_customer.customer_id.startswith("CUS"):
                last_number = int(last_customer.customer_id[3:])
                new_customer_id = f"CUS{last_number + 1}"
            else:
                new_customer_id = "CUS1000001"

            # Create new record
            new_quotation = QuotationCustomer.objects.create(
                customer_id=new_customer_id,
                mobile_number=mobile_number,
                email_address=email_address,
                quote_date=quote_date,
                name_as_per_pan=name_as_per_pan,
                pan_card_number=pan_card_number,
                date_of_birth=date_of_birth,
                state=state,
                city=city,
                pincode=pincode,
                address=address,
                active=True,
            )
            create_quotation(request, new_customer_id)

            messages.success(request, f"Quotation created successfully! Customer ID: {new_customer_id}")

            # Redirect to create-vehicle-info page
            return redirect(reverse("create-vehicle-info", args=[new_customer_id]))

from django.utils import timezone

def create_quotation(request, customer_id):
    quotation, created = Quotation.objects.get_or_create(
        customer_id=customer_id,
        defaults={
            'created_by': str(request.user.id),
            'active': True
        }
    )

    if not created:
        # If it already exists, update something if needed
        quotation.updated_at = timezone.now()
        quotation.save()


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

def fetch_vehicle_info(request):
    if request.method == "POST":
        registration_number = request.POST.get("registration_number", "").strip()
        customer_id = request.POST.get("customer_id", "").strip()

        if not customer_id:
            messages.error(request, "Please create a customer.")
            return redirect("quote-management-create")

        if not registration_number:
            messages.error(request, "Please enter a Registration number.")
            return redirect("quote-management-create")

        customer = get_object_or_404(QuotationCustomer, customer_id=customer_id)
        products = [{'id': 1, 'name': 'Motor'}, {'id': 2, 'name': 'Health'}, {'id': 3, 'name': 'Term'}]
        members = Users.objects.filter(role_id=2, activation_status='1') if request.user.role_id == 1 else Users.objects.none()

        vehicle_detail = QuotationVehicleDetail.objects.filter(registration_number=registration_number).first()
        vehicle_info = VehicleInfo.objects.filter(customer_id=customer_id).first()

        if not vehicle_detail:
            vehicle_data = fetch_vehicle_details_from_api(registration_number)
            if vehicle_data:
                vehicle_detail = QuotationVehicleDetail.objects.create(
                    registration_number=registration_number,
                    vehicle_details=json.dumps(vehicle_data)
                )

                # Log only when API is hit
                store_log(
                    log_type="INFO",
                    log_for="VAHAN_API",
                    message=f"Vahan API called for registration number {registration_number}",
                    user_id=request.user.id if request.user.is_authenticated else None,
                    ip_address=request.META.get("REMOTE_ADDR", "")
                )
        
        vehicle_data = model_to_dict(vehicle_detail) if vehicle_detail else {}
        vehicle_json = {}
        if vehicle_detail and vehicle_detail.vehicle_details:
            try:
                vehicle_json = json.loads(vehicle_detail.vehicle_details)
            except json.JSONDecodeError:
                vehicle_json = {}

        return render(request, 'quote-management/create-vehicle-info.html', {
            'products': products,
            'members': members,
            'cus_id': customer_id,
            'customer': customer,
            'registration_number': registration_number,
            'vehicle_info': vehicle_info,
            'vehicle_detail': vehicle_data,  # Model details
            'vehicle_json': vehicle_json  # Parsed JSON details
        })
    
    return redirect("quote-management-create")

def createVehicleInfo(request, cus_id):
    if not request.user.is_authenticated:
        return redirect('login')
    
    # Fetch existing customer
    customer = get_object_or_404(QuotationCustomer, customer_id=cus_id)
    vehicle_info = VehicleInfo.objects.filter(customer_id=cus_id).first()
    
    if request.method == "GET":
        products = [
            {'id': 1, 'name': 'Motor'},
            {'id': 2, 'name': 'Health'},
            {'id': 3, 'name': 'Term'},
        ]
        
        members = Users.objects.filter(role_id=2, activation_status='1') if request.user.role_id == 1 else Users.objects.none()
        if vehicle_info:
            selected_policy_companies = vehicle_info.policy_companies.split(',') if vehicle_info.policy_companies else []
        else:
            selected_policy_companies = []

        return render(request, 'quote-management/create-vehicle-info.html', {
            'products': products,
            'members': members,
            'cus_id': cus_id,
            'customer': customer,
            'vehicle_info': vehicle_info,
            'selected_policy_companies': selected_policy_companies
        })

    elif request.method == "POST":
        def parse_date(date_str):
            """Convert date string to datetime.date or None if empty."""
            try:
                return datetime.strptime(date_str.strip(), "%Y-%m-%d").date() if date_str.strip() else None
            except ValueError:
                messages.error(request, "Invalid date format.")
                return None

        # Extract and validate form data (existing fields)
        registration_number = request.POST.get("registration_number", "").strip()
        registration_date = parse_date(request.POST.get("registration_date", ""))
        vehicle_type = request.POST.get("vehicle_type", "").strip()
        make = request.POST.get("make", "").strip()
        model = request.POST.get("model", "").strip()
        variant = request.POST.get("variant", "").strip()
        year_of_manufacture = request.POST.get("year_of_manufacture", "").strip() or None
        registration_state = request.POST.get("registration_state", "").strip()
        registration_city = request.POST.get("registration_city", "").strip()
        chassis_number = request.POST.get("chassis_number", "").strip()
        engine_number = request.POST.get("engine_number", "").strip()
        claim_history = request.POST.get("claim_history", "").strip()
        ncb = request.POST.get("ncb", "").strip()
        ncb_percentage = request.POST.get("ncb_percentage", "").strip() or None
        idv_value = request.POST.get("idv_value", "").strip() or None
        policy_type = request.POST.get("policy_type", "").strip()
        policy_duration = request.POST.get("policy_duration", "").strip()
        addons = request.POST.get("addons", "").strip()
        policy_companies = request.POST.getlist("policy_companies[]")
        policy_companies_str = ",".join(policy_companies)

        # Extract new fields for Owner Details & Information
        owner_name = request.POST.get("owner_name", "").strip()
        father_name = request.POST.get("father_name", "").strip()
        state_code = request.POST.get("state_code", "").strip()
        location = request.POST.get("location", "").strip()
        vehicle_category = request.POST.get("vehicle_category", "").strip()
        vehicle_class_description = request.POST.get("vehicle_class_description", "").strip()
        body_type_description = request.POST.get("body_type_description", "").strip()
        vehicle_color = request.POST.get("vehicle_color", "").strip()
        vehicle_cubic_capacity = request.POST.get("vehicle_cubic_capacity", "").strip()
        vehicle_gross_weight = request.POST.get("vehicle_gross_weight", "").strip()
        vehicle_seating_capacity = request.POST.get("vehicle_seating_capacity", "").strip()
        vehicle_fuel_description = request.POST.get("vehicle_fuel_description", "").strip()
        vehicle_owner_number = request.POST.get("vehicle_owner_number", "").strip()
        rc_expiry_date = parse_date(request.POST.get("rc_expiry_date", ""))
        rc_pucc_expiry_date = parse_date(request.POST.get("rc_pucc_expiry_date", ""))

        # Extract new fields for Insurer Details & Information
        insurance_company = request.POST.get("insurance_company", "").strip()
        insurance_expiry_date = parse_date(request.POST.get("insurance_expiry_date", ""))
        insurance_policy_number = request.POST.get("insurance_policy_number", "").strip()

        if vehicle_info:
            # Update existing vehicle info
            vehicle_info.registration_number = registration_number
            vehicle_info.registration_date = registration_date
            vehicle_info.vehicle_type = vehicle_type
            vehicle_info.make = make
            vehicle_info.model = model
            vehicle_info.variant = variant
            vehicle_info.year_of_manufacture = year_of_manufacture
            vehicle_info.registration_state = registration_state
            vehicle_info.registration_city = registration_city
            vehicle_info.chassis_number = chassis_number
            vehicle_info.engine_number = engine_number
            vehicle_info.claim_history = claim_history
            vehicle_info.ncb = ncb
            vehicle_info.ncb_percentage = ncb_percentage
            vehicle_info.idv_value = idv_value
            vehicle_info.policy_type = policy_type
            vehicle_info.policy_duration = policy_duration
            vehicle_info.addons = addons
            vehicle_info.policy_companies = policy_companies_str
            
            # Update new fields
            vehicle_info.owner_name = owner_name
            vehicle_info.father_name = father_name
            vehicle_info.state_code = state_code
            vehicle_info.location = location
            vehicle_info.vehicle_category = vehicle_category
            vehicle_info.vehicle_class_description = vehicle_class_description
            vehicle_info.body_type_description = body_type_description
            vehicle_info.vehicle_color = vehicle_color
            vehicle_info.vehicle_cubic_capacity = vehicle_cubic_capacity
            vehicle_info.vehicle_gross_weight = vehicle_gross_weight
            vehicle_info.vehicle_seating_capacity = vehicle_seating_capacity
            vehicle_info.vehicle_fuel_description = vehicle_fuel_description
            vehicle_info.vehicle_owner_number = vehicle_owner_number
            vehicle_info.rc_expiry_date = rc_expiry_date
            vehicle_info.rc_pucc_expiry_date = rc_pucc_expiry_date
            vehicle_info.insurance_company = insurance_company
            vehicle_info.insurance_expiry_date = insurance_expiry_date
            vehicle_info.insurance_policy_number = insurance_policy_number

            vehicle_info.active = True
            vehicle_info.save()
            messages.success(request, "Vehicle information updated successfully!")
        else:
            # Create new vehicle info record
            VehicleInfo.objects.create(
                customer_id=cus_id,
                registration_number=registration_number,
                registration_date=registration_date,
                vehicle_type=vehicle_type,
                make=make,
                model=model,
                variant=variant,
                year_of_manufacture=year_of_manufacture,
                registration_state=registration_state,
                registration_city=registration_city,
                chassis_number=chassis_number,
                engine_number=engine_number,
                claim_history=claim_history,
                ncb=ncb,
                ncb_percentage=ncb_percentage,
                idv_value=idv_value,
                policy_type=policy_type,
                policy_duration=policy_duration,
                addons=addons,
                policy_companies=policy_companies_str,
                # New fields
                owner_name=owner_name,
                father_name=father_name,
                state_code=state_code,
                location=location,
                vehicle_category=vehicle_category,
                vehicle_class_description=vehicle_class_description,
                body_type_description=body_type_description,
                vehicle_color=vehicle_color,
                vehicle_cubic_capacity=vehicle_cubic_capacity,
                vehicle_gross_weight=vehicle_gross_weight,
                vehicle_seating_capacity=vehicle_seating_capacity,
                vehicle_fuel_description=vehicle_fuel_description,
                vehicle_owner_number=vehicle_owner_number,
                rc_expiry_date=rc_expiry_date,
                rc_pucc_expiry_date=rc_pucc_expiry_date,
                insurance_company=insurance_company,
                insurance_expiry_date=insurance_expiry_date,
                insurance_policy_number=insurance_policy_number,
                active=True,
            )
            messages.success(request, "Vehicle information added successfully!")

        # create_or_update_lead(request, cus_id)
        return redirect(reverse("show-quotation-info", args=[cus_id]))


def showQuotation(request, cus_id):
    if not request.user.is_authenticated:
        return redirect('login')

    products = [
        {'id': 1, 'name': 'Motor'},
        {'id': 2, 'name': 'Health'},
        {'id': 3, 'name': 'Term'},
    ]

    members = Users.objects.filter(role_id=2, activation_status='1') if request.user.role_id == 1 else Users.objects.none()

    customer = get_object_or_404(QuotationCustomer, customer_id=cus_id)
    vehicle_info = VehicleInfo.objects.filter(customer_id=cus_id).first()

    ADDONS_MAP = {
        "1": "Zero Depreciation",
        "2": "Roadside Assistance",
        "3": "Engine Protection"
    }
    addons_list = vehicle_info.addons.split(",") if vehicle_info.addons else []

    # Convert add-on IDs to names using ADDONS_MAP
    addon_names = [ADDONS_MAP.get(addon.strip(), "Unknown Add-on") for addon in addons_list]

    if vehicle_info:
        selected_policy_companies = vehicle_info.policy_companies.split(',') if vehicle_info.policy_companies else []
    else:
        selected_policy_companies = []
    INSURER_MAP = {
        "1": "Bajaj Allianz",
        "2": "Reliance General",
        "3": "SBI General",
        "4": "New India Assurance",
        "5": "Oriental Insurance",
        "6": "United India Insurance",
        "7": "Future Generali",
        "8": "IFFCO Tokio",
        "9": "Cholamandalam MS",
        "10": "Kotak Mahindra",
    }
    
    selected_policy_companies_names = [INSURER_MAP[comp_id] for comp_id in selected_policy_companies if comp_id in INSURER_MAP]

    plan_names = ["Comprehensive Plan A", "Comprehensive Secure", "Auto Secure Plan"]
    premium_amounts = ["INR12,500", "INR11,800", "INR13,200"]
    policy_types = ["Comprehensive", "Comprehensive", "Comprehensive"]
    idv = ["INR5,00,000", "INR4,80,000", "INR5,20,000"]
    ncb_discount = ["20%", "25%", "18%"]
    own_damage_premium = ["INR7,500", "INR7,000", "INR8,000"]
    third_party_premium = ["INR4,500", "INR4,800", "INR5,200"]
    addons = ["Zero Dep, Roadside Assist", "Zero Dep, Engine Protect", "Zero Dep, Key Replacement"]
    claim_ratio = ["95%", "93%", "97%"]
    garage_network = ["5000+", "4500+", "5500+"]
    tenure = ["1 Year", "1 Year", "1 Year"]
    deductibles = ["INR1,000", "INR750", "INR1,500"]

    # Fetch saved quotation form data (if exists)
    try:
        quotation_data_obj = QuotationFormData.objects.get(customer_id=cus_id)
        saved_form_data = json.loads(quotation_data_obj.form_data)
    except QuotationFormData.DoesNotExist:
        saved_form_data = {}

    if saved_form_data:
        data_dict = saved_form_data
    else:
        data_dict = {}

    return render(request, 'quote-management/show-quotation-info.html', {
        'products': products,
        'members': members,
        'cus_id': cus_id,
        'vehicle_info': vehicle_info,
        'selected_policy_companies': selected_policy_companies_names,
        'plan_names': plan_names,
        'premium_amounts': premium_amounts,
        'policy_types': policy_types,
        'idv': idv,
        'ncb_discount': ncb_discount,
        'own_damage_premium': own_damage_premium,
        'third_party_premium': third_party_premium,
        'addons': addons,
        'claim_ratio': claim_ratio,
        'saved_form_data': saved_form_data,
        'data_dict': data_dict,  # add this
        'garage_network': garage_network,
        'tenure': tenure,
        'deductibles': deductibles,
        'addons_map': ADDONS_MAP,
        'customer': customer,
        'addon_names': addon_names,  # Pass formatted add-ons list
    })


def saveQuotationData(request):
    if request.method == 'POST':
        form_data = request.POST.dict()
        customer_id = form_data.pop('customer_id', None)

        if not customer_id:
            return JsonResponse({'message': 'Customer ID is missing.'}, status=400)

        # Save or update the serialized data
        form_data_json = json.dumps(form_data)
        quotation, created = QuotationFormData.objects.update_or_create(
            customer_id=customer_id,
            defaults={'form_data': form_data_json}
        )

        message = 'Quotation data created successfully.' if created else 'Quotation data updated successfully.'
        return JsonResponse({'message': message})

    return JsonResponse({'message': 'Invalid request method.'}, status=405)

def downloadQuotationPdf(request, cus_id):
    if not request.user.is_authenticated:
        return redirect('login')

    wkhtml_path = os.getenv('WKHTML_PATH', r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe')
    config = pdfkit.configuration(wkhtmltopdf=wkhtml_path)

    products = [
        {'id': 1, 'name': 'Motor'},
        {'id': 2, 'name': 'Health'},
        {'id': 3, 'name': 'Term'},
    ]

    members = Users.objects.filter(role_id=2, activation_status='1') if request.user.role_id == 1 else Users.objects.none()

    customer = get_object_or_404(QuotationCustomer, customer_id=cus_id)
    vehicle_info = VehicleInfo.objects.filter(customer_id=cus_id).first()

    ADDONS_MAP = {
        "1": "Zero Depreciation",
        "2": "Roadside Assistance",
        "3": "Engine Protection"
    }
    addons_list = vehicle_info.addons.split(",") if vehicle_info and vehicle_info.addons else []
    addon_names = [ADDONS_MAP.get(addon.strip(), "Unknown Add-on") for addon in addons_list]

    INSURER_MAP = {
        "1": "Bajaj Allianz",
        "2": "Reliance General",
        "3": "SBI General",
        "4": "New India Assurance",
        "5": "Oriental Insurance",
        "6": "United India Insurance",
        "7": "Future Generali",
        "8": "IFFCO Tokio",
        "9": "Cholamandalam MS",
        "10": "Kotak Mahindra",
    }
    selected_policy_companies = vehicle_info.policy_companies.split(',') if vehicle_info and vehicle_info.policy_companies else []
    selected_policy_companies_names = [INSURER_MAP[comp_id] for comp_id in selected_policy_companies if comp_id in INSURER_MAP]

    plan_names = ["Comprehensive Plan A", "Comprehensive Secure", "Auto Secure Plan"]
    premium_amounts = ["INR12,500", "INR11,800", "INR13,200"]
    policy_types = ["Comprehensive", "Comprehensive", "Comprehensive"]
    idv = ["INR5,00,000", "INR4,80,000", "INR5,20,000"]
    ncb_discount = ["20%", "25%", "18%"]
    own_damage_premium = ["INR7,500", "INR7,000", "INR8,000"]
    third_party_premium = ["INR4,500", "INR4,800", "INR5,200"]
    addons = ["Zero Dep, Roadside Assist", "Zero Dep, Engine Protect", "Zero Dep, Key Replacement"]
    claim_ratio = ["95%", "93%", "97%"]
    garage_network = ["5000+", "4500+", "5500+"]
    tenure = ["1 Year", "1 Year", "1 Year"]
    deductibles = ["INR1,000", "INR750", "INR1,500"]



    # Fetch saved quotation form data (if exists)
    try:
        quotation_data_obj = QuotationFormData.objects.get(customer_id=cus_id)
        saved_form_data = json.loads(quotation_data_obj.form_data)
    except QuotationFormData.DoesNotExist:
        saved_form_data = {}

    if saved_form_data:
        data_dict = saved_form_data
    else:
        data_dict = {}

    context = {
        "customer": customer,
        "vehicle_info": vehicle_info,
        "addon_names": addon_names,
        "products": products,
        "members": members,
        "selected_policy_companies": selected_policy_companies_names,
        "plan_names": plan_names,
        "premium_amounts": premium_amounts,
        "policy_types": policy_types,
        "idv": idv,
        "ncb_discount": ncb_discount,
        "own_damage_premium": own_damage_premium,
        "third_party_premium": third_party_premium,
        "addons": addons,
        "claim_ratio": claim_ratio,
        "garage_network": garage_network,
        "tenure": tenure,
        "deductibles": deductibles,
        "data_dict": data_dict,
        "addons_map": ADDONS_MAP,
        "logo_url": os.path.join(settings.BASE_DIR, getattr(settings, 'LOGO_WITH_EMP_PORTAL', 'empPortal/static/dist/img/logo2.png')),
    }

    html_content = render_to_string("quote-management/show-quotation-pdf.html", context)

    options = {
        'enable-local-file-access': '',
        'page-size': 'A4',
        'encoding': "UTF-8",
    }

    pdf = pdfkit.from_string(html_content, False, configuration=config, options=options)

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="quotation_{cus_id}.pdf"'

    return response


def sendQuotationPdfEmail(request, cus_id):
    if not request.user.is_authenticated:
        return redirect('login')

    customer = get_object_or_404(QuotationCustomer, customer_id=cus_id)
    recipient_email = customer.email_address

    # Generate PDF content using the existing function
    wkhtml_path = os.getenv('WKHTML_PATH', r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe')
    config = pdfkit.configuration(wkhtmltopdf=wkhtml_path)

    products = [
        {'id': 1, 'name': 'Motor'},
        {'id': 2, 'name': 'Health'},
        {'id': 3, 'name': 'Term'},
    ]

    members = Users.objects.filter(role_id=2, activation_status='1') if request.user.role_id == 1 else Users.objects.none()

    vehicle_info = VehicleInfo.objects.filter(customer_id=cus_id).first()

    ADDONS_MAP = {
        "1": "Zero Depreciation",
        "2": "Roadside Assistance",
        "3": "Engine Protection"
    }
    addons_list = vehicle_info.addons.split(",") if vehicle_info and vehicle_info.addons else []
    addon_names = [ADDONS_MAP.get(addon.strip(), "Unknown Add-on") for addon in addons_list]

    INSURER_MAP = {
        "1": "Bajaj Allianz",
        "2": "Reliance General",
        "3": "SBI General",
        "4": "New India Assurance",
        "5": "Oriental Insurance",
        "6": "United India Insurance",
        "7": "Future Generali",
        "8": "IFFCO Tokio",
        "9": "Cholamandalam MS",
        "10": "Kotak Mahindra",
    }
    selected_policy_companies = vehicle_info.policy_companies.split(',') if vehicle_info and vehicle_info.policy_companies else []
    selected_policy_companies_names = [INSURER_MAP[comp_id] for comp_id in selected_policy_companies if comp_id in INSURER_MAP]

    plan_names = ["Comprehensive Plan A", "Comprehensive Secure", "Auto Secure Plan"]
    premium_amounts = ["INR12,500", "INR11,800", "INR13,200"]
    policy_types = ["Comprehensive", "Comprehensive", "Comprehensive"]
    idv = ["INR5,00,000", "INR4,80,000", "INR5,20,000"]
    ncb_discount = ["20%", "25%", "18%"]
    own_damage_premium = ["INR7,500", "INR7,000", "INR8,000"]
    third_party_premium = ["INR4,500", "INR4,800", "INR5,200"]
    addons = ["Zero Dep, Roadside Assist", "Zero Dep, Engine Protect", "Zero Dep, Key Replacement"]
    claim_ratio = ["95%", "93%", "97%"]
    garage_network = ["5000+", "4500+", "5500+"]
    tenure = ["1 Year", "1 Year", "1 Year"]
    deductibles = ["INR1,000", "INR750", "INR1,500"]


    # Fetch saved quotation form data (if exists)
    try:
        quotation_data_obj = QuotationFormData.objects.get(customer_id=cus_id)
        saved_form_data = json.loads(quotation_data_obj.form_data)
    except QuotationFormData.DoesNotExist:
        saved_form_data = {}

    if saved_form_data:
        data_dict = saved_form_data
    else:
        data_dict = {}

    context = {
        "customer": customer,
        "vehicle_info": vehicle_info,
        "addon_names": addon_names,
        "products": products,
        "members": members,
        "selected_policy_companies": selected_policy_companies_names,
        "plan_names": plan_names,
        "premium_amounts": premium_amounts,
        "policy_types": policy_types,
        "idv": idv,
        "ncb_discount": ncb_discount,
        "own_damage_premium": own_damage_premium,
        "third_party_premium": third_party_premium,
        "addons": addons,
        "claim_ratio": claim_ratio,
        "garage_network": garage_network,
        "tenure": tenure,
        "deductibles": deductibles,
        "data_dict": data_dict,
        "addons_map": ADDONS_MAP,
        "logo_url": request.build_absolute_uri(static('dist/img/logo2.png')),
    }

    html_content = render_to_string("quote-management/show-quotation-pdf.html", context)

    options = {
        'enable-local-file-access': '',
        'page-size': 'A4',
        'encoding': "UTF-8",
    }

    pdf = pdfkit.from_string(html_content, False, configuration=config, options=options)

    # Prepare email
    # Use the correct attribute for the customer's name.  It's likely to be 'customer.name'
    subject = f"Quotation for {customer.name_as_per_pan}"  # Change this line
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [recipient_email]

    email = EmailMessage(subject, "Please find your quotation attached.", from_email, recipient_list)
    email.attach(f"quotation_{cus_id}.pdf", pdf, 'application/pdf')

    try:
        email.send()
        messages.success(request, "Quotation sent successfully!")
    except Exception as e:
        logger.error(f"Error sending quotation email: {e}")
        messages.error(request, "Failed to send quotation email.")

    return redirect('show-quotation-info', cus_id=cus_id)
    
def store(request):
    if not request.user.is_authenticated:
        return redirect('login')

    if request.method == "POST":
        member_id = request.POST.get('member', '').strip()
        product_id = request.POST.get('product', '').strip()
        tp_percentage = request.POST.get('tp_percentage', '').strip()
        od_percentage = request.POST.get('od_percentage', '').strip()
        net_percentage = request.POST.get('net_percentage', '').strip()

        # Validations
        if not member_id:
            messages.error(request, "Member is required.")
        if not product_id:
            messages.error(request, "Product is required.")
        if not tp_percentage or not tp_percentage.replace('.', '', 1).isdigit():
            messages.error(request, "Valid TP percentage is required.")
        if not od_percentage or not od_percentage.replace('.', '', 1).isdigit():
            messages.error(request, "Valid OD percentage is required.")
        if not net_percentage or not net_percentage.replace('.', '', 1).isdigit():
            messages.error(request, "Valid Net percentage is required.")

        # Check if this sub-broker already has a commission for the selected insurer
        if Commission.objects.filter(member_id=member_id, product_id=product_id).exists():
            messages.error(request, "You already have a commission for this member & product.")

        # If any errors, redirect back to the 'add-commission' page
        if messages.get_messages(request):
            return redirect('add-commission')

        # Save to database
        Commission.objects.create(
            product_id=product_id,
            member_id=member_id,
            tp_percentage=float(tp_percentage),
            od_percentage=float(od_percentage),
            net_percentage=float(net_percentage),
            created_by=request.user.id
        )


        messages.success(request, "Commission added successfully.")
        return redirect('commissions')

    else:
        messages.error(request, "Invalid request.")
        return redirect('add-commission')