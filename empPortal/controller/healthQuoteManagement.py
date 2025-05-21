from django.shortcuts import render,redirect, get_object_or_404
from ..models import Commission, Users, QuotationCustomer, VehicleInfo, QuotationVehicleDetail
from django.db.models import OuterRef, Subquery
from django.contrib import messages
from datetime import datetime
from django.urls import reverse
import pprint  # Import pprint for better formatting
from django.http import JsonResponse
import pdfkit
import os
from django.conf import settings
import os
from dotenv import load_dotenv
from django.templatetags.static import static  # ✅ Import static
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.forms.models import model_to_dict
import json

def dictfetchall(cursor):
    "Returns all rows from a cursor as a dict"
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

def index(request):
    if not request.user.is_authenticated or request.user.is_active != 1:
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

    # Base QuerySet
    quotations = QuotationCustomer.objects.all()

    # Apply filters dynamically
    if customer_id:
        quotations = quotations.filter(customer_id=customer_id)
    if customer_name:
        quotations = quotations.filter(name_as_per_pan__icontains=customer_name)
    if customer_mobile:
        quotations = quotations.filter(mobile_number__icontains=customer_mobile)
    # if policy_type:
    #     quotations = quotations.filter(vehicleinfo__policy_type__icontains=policy_type)
    # if quote_status:
    #     quotations = quotations.filter(status__icontains=quote_status)
    # if vehicle_type:
    #     quotations = quotations.filter(vehicleinfo__vehicle_type__icontains=vehicle_type)
    # if ncb:
    #     quotations = quotations.filter(vehicleinfo__ncb_percentage=ncb)
    # if insurer_name:
    #     quotations = quotations.filter(vehicleinfo__insurer_name__icontains=insurer_name)

    # Handle date range filtering
    if quote_date_range:
        try:
            start_date, end_date = map(str.strip, quote_date_range.split(" - "))
            quotations = quotations.filter(created_at__range=[start_date, end_date])
        except ValueError:
            pass  # Ignore invalid date format

    # Fetch latest vehicle information
    latest_vehicle_info = VehicleInfo.objects.filter(
        customer_id=OuterRef('customer_id')
    ).order_by('-created_at')

    # Annotate vehicle information properly
    quotations_with_vehicle = quotations.annotate(
        registration_number=Subquery(latest_vehicle_info.values('registration_number')[:1]),
        vehicle_type=Subquery(latest_vehicle_info.values('vehicle_type')[:1]),
        make=Subquery(latest_vehicle_info.values('make')[:1]),  # ✅ Fixed reference
        model=Subquery(latest_vehicle_info.values('model')[:1]),  # ✅ Fixed reference
        year_of_manufacture=Subquery(latest_vehicle_info.values('year_of_manufacture')[:1]),
        policy_type=Subquery(latest_vehicle_info.values('policy_type')[:1]),
        idv_value=Subquery(latest_vehicle_info.values('idv_value')[:1]),
        claim_history=Subquery(latest_vehicle_info.values('claim_history')[:1]),
        ncb_percentage=Subquery(latest_vehicle_info.values('ncb_percentage')[:1]),
        addons=Subquery(latest_vehicle_info.values('addons')[:1]),
    )

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
        }

        customer_data['vehicle'] = vehicle_data if quotation.registration_number else {}

        if customer_data["vehicle"].get("addons"):
            addons_key = str(customer_data["vehicle"]["addons"])
            customer_data["vehicle"]["addons_display"] = ADDONS_MAP.get(addons_key, "N/A")
        else:
            customer_data["vehicle"]["addons_display"] = "N/A"

        data.append(customer_data)
        
    return render(request, 'health-quote-management/index.html', {'quotations': data})


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

        return render(request, 'quote-management/create.html', {
            'products': products,
            'members': members,
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

            messages.success(request, f"Quotation created successfully! Customer ID: {new_customer_id}")

            # Redirect to create-vehicle-info page
            return redirect(reverse("create-vehicle-info", args=[new_customer_id]))



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

        # Convert model instance to dict
        vehicle_data = model_to_dict(vehicle_detail) if vehicle_detail else {}

        # Parse vehicle_details JSON if it exists
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
            'vehicle_info': vehicle_info,  # Existing data
            'selected_policy_companies': selected_policy_companies  # List for template
        })


    elif request.method == "POST":
        def parse_date(date_str):
            """Convert date string to datetime.date or None if empty."""
            try:
                return datetime.strptime(date_str.strip(), "%Y-%m-%d").date() if date_str.strip() else None
            except ValueError:
                messages.error(request, "Invalid date format.")
                return None

        # Extract and validate form data
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
        
        policy_companies = request.POST.getlist("policy_companies[]")  # Returns a list
        policy_companies_str = ",".join(policy_companies)  # Convert list to string

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
                active=True,
            )
            messages.success(request, "Vehicle information added successfully!")
        

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

    return render(request, 'quote-management/show-quotation-info.html', {
        'products': products,
        'members': members,
        'cus_id': cus_id,
        'vehicle_info': vehicle_info,
        'addons_map': ADDONS_MAP,
        'customer': customer,
        'addon_names': addon_names,  # Pass formatted add-ons list
    })


def downloadQuotationPdf(request, cus_id):
    if not request.user.is_authenticated:
        return redirect('login')

    wkhtml_path = os.getenv('WKHTML_PATH', r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe')
    config = pdfkit.configuration(wkhtmltopdf=wkhtml_path)

    # Fetch customer and vehicle details
    customer = get_object_or_404(QuotationCustomer, customer_id=cus_id)
    vehicle_info = VehicleInfo.objects.filter(customer_id=cus_id).first()

    # Add-ons mapping
    ADDONS_MAP = {
        "1": "Zero Depreciation",
        "2": "Roadside Assistance",
        "3": "Engine Protection"
    }
    addons_list = vehicle_info.addons.split(",") if vehicle_info and vehicle_info.addons else []
    addon_names = [ADDONS_MAP.get(addon.strip(), "Unknown Add-on") for addon in addons_list]

    # Data to pass to the template
    context = {
        "customer": customer,
        "vehicle_info": vehicle_info,
        "addon_names": addon_names,
        "logo_url": request.build_absolute_uri(static('dist/img/logo.png'))
    }

    # Render HTML template with context data
    html_content = render_to_string("quote-management/show-quotation-pdf.html", context)

    options = {
        'enable-local-file-access': '',
        'page-size': 'A4',
        'encoding': "UTF-8",
    }

    # Generate PDF from HTML content
    pdf = pdfkit.from_string(html_content, False, configuration=config, options=options)

    # Create HTTP response with PDF as an attachment
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="quotation_{cus_id}.pdf"'

    return response

    
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