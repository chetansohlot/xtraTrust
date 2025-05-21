import re
from django.shortcuts import render,redirect
from ..models import Commission,Users, QuotationCustomer

from django.contrib.auth import authenticate, login ,logout
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator

from django.shortcuts import get_object_or_404
from django.utils.timezone import now
from datetime import datetime
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt


def dictfetchall(cursor):
    "Returns all rows from a cursor as a dict"
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def customers(request):
    if not request.user.is_authenticated:
        return redirect('login')

    if request.user.role_id == 1:
        per_page = request.GET.get('per_page', 10)
        search_field = request.GET.get('search_field', '')  # Field to search
        search_query = request.GET.get('search_query', '')  # Search value
        sorting = request.GET.get('sorting', '')  # Sorting option

        try:
            per_page = int(per_page)
        except ValueError:
            per_page = 10  # Default to 10 if invalid value is given

        # Base QuerySet
        customers = QuotationCustomer.objects.all()

        # Apply filtering
        if search_field and search_query:
            filter_args = {f"{search_field}__icontains": search_query}
            customers = customers.filter(**filter_args)


        
        # Apply filters based on form input
        if 'customer_id' in request.GET and request.GET['customer_id']:
            customers = customers.filter(customer_id__icontains=request.GET['customer_id'])
        if 'name_as_per_pan' in request.GET and request.GET['name_as_per_pan']:
           customers = customers.filter(name_as_per_pan__icontains=request.GET['name_as_per_pan'])
        if 'email_address' in request.GET and request.GET['email_address']:
           customers = customers.filter(email_address__icontains=request.GET['email_address'])
        if 'mobile_number' in request.GET and request.GET['mobile_number']:
           customers = customers.filter(mobile_number__icontains=request.GET['mobile_number']) 



        # Apply sorting
        if sorting == "name_a_z":
            customers = customers.order_by("name")
        elif sorting == "name_z_a":
            customers = customers.order_by("-name")
        elif sorting == "recently_updated":
            customers = customers.order_by("-updated_at")
        else:
            customers = customers.order_by("-updated_at")

        total_count = customers.count()

        # Paginate results
        paginator = Paginator(customers, per_page)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        return render(request, 'customers/customers.html', {
            'page_obj': page_obj,
            'total_count': total_count,
            'search_field': search_field,
            'search_query': search_query,
            'sorting': sorting,
            'per_page': per_page,
        })
    else:
        return redirect('login')
    

def create_or_edit(request, customer_id=None):
    if not request.user.is_authenticated:
        return redirect('login')

    # Fetch existing customer if editing
    quotation_customer = None
    if customer_id:
        quotation_customer = get_object_or_404(QuotationCustomer, id=customer_id)

    if request.method == "GET":
        return render(request, 'customers/create.html', {'quotation_customer': quotation_customer})

    elif request.method == "POST":
        # Extract form data
        mobile_number = request.POST.get("mobile_number", "").strip()
        email_address = request.POST.get("email_address", "").strip()
        # quote_date = request.POST.get("quote_date", None)
        name_as_per_pan = request.POST.get("name_as_per_pan", "").strip()
        pan_card_number = request.POST.get("pan_card_number", "").strip() or None
        date_of_birth = request.POST.get("date_of_birth", None)
        state = request.POST.get("state", "").strip()
        city = request.POST.get("city", "").strip()
        pincode = request.POST.get("pincode", "").strip()
        address = request.POST.get("address", "").strip()

        # Validate and format date fields
        try:
            # quote_date = datetime.strptime(quote_date, "%Y-%m-%d").date() if quote_date else None
            date_of_birth = datetime.strptime(date_of_birth, "%Y-%m-%d").date() if date_of_birth else None
        except ValueError:
            messages.error(request, "Invalid date format.")
            return redirect(reverse("quotation-customer-create") if not customer_id else reverse("quotation-customer-edit", args=[customer_id]))

        # Check for uniqueness of mobile number and email address
        # if QuotationCustomer.objects.exclude(id=customer_id).filter(mobile_number=mobile_number).exists():
        #     messages.error(request, "Mobile number is already registered.")
        #     return redirect(reverse("quotation-customer-create") if not customer_id else reverse("quotation-customer-edit", args=[customer_id]))
        
        # if QuotationCustomer.objects.exclude(id=customer_id).filter(email_address=email_address).exists():
        #     messages.error(request, "Email address is already registered.")
        #     return redirect(reverse("quotation-customer-create") if not customer_id else reverse("quotation-customer-edit", args=[customer_id]))
        
        ### validation ----parth ##
        if not mobile_number:
            messages.error(request,"Mobile number is required.")
            return redirect(reverse("quotation-customer-create") if not customer_id else reverse("quotation-customer-edit", args=[customer_id]))

        elif not re.match(r"^[6-9]\d{9}$",mobile_number):
            messages.error(request,"Invalid mobile number.")
            return redirect(reverse("quotation-customer-create") if not customer_id else reverse("quotation-customer-edit", args=[customer_id]))
        
        # Check for uniqueness of mobile number-----
        elif QuotationCustomer.objects.exclude(id=customer_id).filter(mobile_number=mobile_number).exists():
            messages.error(request, "Mobile number is already registered.")
            return redirect(reverse("quotation-customer-create") if not customer_id else reverse("quotation-customer-edit", args=[customer_id]))
        
        if not email_address or "@" not in email_address:
            messages.error(request,"Invalid email address.")
            return redirect(reverse("quotation-customer-create") if not customer_id else reverse("quotation-customer-edit", args=[customer_id]))
        
        elif QuotationCustomer.objects.exclude(id=customer_id).filter(email_address=email_address).exists():
            messages.error(request, "Email address is already registered.")
            return redirect(reverse("quotation-customer-create") if not customer_id else reverse("quotation-customer-edit", args=[customer_id]))

        if not name_as_per_pan or len(name_as_per_pan) < 3: 
            messages.error(request,"Name as per PAN must be at least 3 characters.")   
            return redirect(reverse("quotation-customer-create") if not customer_id else reverse("quotation-customer-edit", args=[customer_id]))
        
        if not pan_card_number:
            messages.error(request,'PAN card number is required.')
            
        elif not re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]$', pan_card_number):
            messages.error(request, 'Enter a valid PAN card number (e.g., ABCDE1234F).')
            return redirect(reverse("quotation-customer-create") if not customer_id else reverse("quotation-customer-edit", args=[customer_id]))


        if not pincode or not pincode.isdigit() or len(pincode) != 6 or pincode.startswith('0'):
            messages.error(request,"Invalid pincode. It must be 6 digit not start with 0")
            return redirect(reverse("quotation-customer-create") if not customer_id else reverse("quotation-customer-edit", args=[customer_id]))

        if not address or len(address) < 5:
            messages.error(request,"Address must be at least 5 characters.")
            return redirect(reverse("quotation-customer-create") if not customer_id else reverse("quotation-customer-edit", args=[customer_id]))
        
        if not state:
            messages.error(request,"State is required.")
            return redirect(reverse("quotation-customer-create") if not customer_id else reverse("quotation-customer-edit", args=[customer_id]))
        elif not re.match(r"^[A-Za-z\s]+$",state):
            messages.error(request,"State Name Must contains only alphabets.")
            return redirect(reverse("quotation-customer-create") if not customer_id else reverse("quotation-customer-edit", args=[customer_id]))

        if not city:
            messages.error(request,"City is required.")
            return redirect(reverse("quotation-customer-create") if not customer_id else reverse("quotation-customer-edit", args=[customer_id]))
        elif not re.match(r"^[A-Za-z\s]+$",city):
            messages.error(request,"City Name Must contains only alphabets.")
            return redirect(reverse("quotation-customer-create") if not customer_id else reverse("quotation-customer-edit", args=[customer_id]))






        if quotation_customer:
            # Update existing record
            quotation_customer.mobile_number = mobile_number
            quotation_customer.email_address = email_address
            # quotation_customer.quote_date = quote_date
            quotation_customer.name_as_per_pan = name_as_per_pan
            quotation_customer.pan_card_number = pan_card_number
            quotation_customer.date_of_birth = date_of_birth
            quotation_customer.state = state
            quotation_customer.city = city
            quotation_customer.pincode = pincode
            quotation_customer.address = address
            quotation_customer.updated_at = now()
            quotation_customer.save()

            messages.success(request, f"Quotation Customer updated successfully! Customer ID: {quotation_customer.customer_id}")

            return redirect("customers")  # Redirect to customers list or another page

        else:
            # Generate new customer_id
            last_customer = QuotationCustomer.objects.order_by('-id').first()
            if last_customer and last_customer.customer_id.startswith("CUS"):
                last_number = int(last_customer.customer_id[3:])
                new_customer_id = f"CUS{last_number + 1}"
            else:
                new_customer_id = "CUS1000001"

            # Create new record
            new_quotation_customer = QuotationCustomer.objects.create(
                customer_id=new_customer_id,
                mobile_number=mobile_number,
                email_address=email_address,
                # quote_date=quote_date,
                name_as_per_pan=name_as_per_pan,
                pan_card_number=pan_card_number,
                date_of_birth=date_of_birth,
                state=state,
                city=city,
                pincode=pincode,
                address=address,
                active=True,
                created_at=now(),
                updated_at=now()
            )

            messages.success(request, f"Quotation Customer created successfully! Customer ID: {new_customer_id}")

            # Redirect to the next page (e.g., vehicle info)
            return redirect('customers')



    
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

#Anjali
@csrf_exempt
def toggle_customer_status(request, customer_id):
    if request.method == "POST": 
        try:
            customer = get_object_or_404(QuotationCustomer, id=customer_id)
            status = request.POST.get("status")  # Get status from AJAX request

            if status == "1":
                customer.active = True  # Set Active
            else:
                customer.active = False  # Set Inactive

            customer.save()  # Save changes in the database

            return JsonResponse({"success": True, "status": customer.active})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})
    
    return JsonResponse({"success": False, "error": "Invalid request method"})