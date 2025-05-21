from django.shortcuts import render,redirect, get_object_or_404
from ..models import Franchise, Franchises
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
from django.utils.timezone import now
from django.utils import timezone
from django.core.paginator import Paginator
from django.core.paginator import Paginator
from django.http import JsonResponse

def dictfetchall(cursor):
    "Returns all rows from a cursor as a dict"
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]





def index(request):
    if not request.user.is_authenticated:
        return redirect('login')

    per_page = request.GET.get('per_page', 10)
    try:
        per_page = int(per_page)
    except ValueError:
        per_page = 10

    # Initial queryset
    franchises = Franchise.objects.all()

    # Filter by optional query params
    name = request.GET.get('name')
    mobile = request.GET.get('mobile')
    email = request.GET.get('email')
    pan_number = request.GET.get('pan_number')

    if name:
        franchises = franchises.filter(franchise_name__icontains=name)
    if mobile:
        franchises = franchises.filter(parent_broker_code__icontains=mobile)  # Adjust field if needed
    if email:
        franchises = franchises.filter(franchise_code__icontains=email)       # Adjust field if needed
    if pan_number:
        franchises = franchises.filter(channel_type__icontains=pan_number)    # Adjust field if needed

    # Sorting logic
    sort_by = request.GET.get('sort_by', '')
    if sort_by == "name_asc":
        franchises = franchises.order_by('franchise_name')
    elif sort_by == "name_desc":
        franchises = franchises.order_by('-franchise_name')
    elif sort_by == "recently_activated":
        franchises = franchises.filter(franchise_status='Active').order_by('-created_at')
    elif sort_by == "recently_deactivated":
        franchises = franchises.filter(franchise_status='Inactive').order_by('-updated_at')
    else:
        franchises = franchises.order_by('-created_at')

    total_count = franchises.count()

    # Pagination
    paginator = Paginator(franchises, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'franchises/index.html', {
        'page_obj': page_obj,
        'total_count': total_count,
        'per_page': per_page,
        # 'sort_by': sort_by,
        'franchises': page_obj,  # Use page object in template
    })



# def create_or_edit(request, franchise_id=None):
#     if not request.user.is_authenticated:
#         return redirect('login')

#     # Fetch existing franchise if editing
#     franchise = None
#     if franchise_id:
#         franchise = get_object_or_404(Franchises, id=franchise_id)

#     if request.method == "GET":
            
#         return render(request, 'franchises/create-basic-detail.html', {
#             'franchise': franchise  # Pass existing data if editing
#         })
    
#     elif request.method == "POST":
#         # Extract form data
#         name = request.POST.get("name", "").strip()
#         contact_person = request.POST.get("contact_person", "").strip()
#         mobile = request.POST.get("mobile", "").strip()
#         email = request.POST.get("email", "").strip()
#         address = request.POST.get("address", "").strip()
#         city = request.POST.get("city", "").strip()
#         state = request.POST.get("state", "").strip()
#         pincode = request.POST.get("pincode", "").strip()
#         gst_number = request.POST.get("gst_number", "").strip() or None
#         pan_number = request.POST.get("pan_number", "").strip() or None
#         registration_no = request.POST.get("registration_no", "").strip() or None
        
#         if franchise:
#             # Update existing record
#             franchise.name = name
#             franchise.contact_person = contact_person
#             franchise.mobile = mobile
#             franchise.email = email
#             franchise.address = address
#             franchise.city = city
#             franchise.state = state
#             franchise.pincode = pincode
#             franchise.gst_number = gst_number
#             franchise.pan_number = pan_number
#             franchise.registration_no = registration_no
#             franchise.updated_at = now()
#             franchise.save()

#             messages.success(request, f"Franchise updated successfully! Franchise ID: {franchise.id}")
#             return redirect(reverse("franchise-management"))  # Redirect to franchise listing

#         else:
#             # Create new record
#             new_franchise = Franchises.objects.create(
#                 name=name,
#                 contact_person=contact_person,
#                 mobile=mobile,
#                 email=email,
#                 address=address,
#                 city=city,
#                 state=state,
#                 pincode=pincode,
#                 gst_number=gst_number,
#                 pan_number=pan_number,
#                 registration_no=registration_no,
#                 created_at=now(),
#                 updated_at=now(),
#             )

#             messages.success(request, f"Franchise created successfully! Franchise ID: {new_franchise.id}")
#             return redirect(reverse("franchise-management"))  # Redirect to franchise listing

#Anjali#

def franchise_toggle_status(request, franchise_id):
    if request.method == "POST":
        franchise = get_object_or_404(Franchise, id=franchise_id)

        # Toggle status
        if franchise.franchise_status == "Active":
            franchise.franchise_status = "Inactive"
        else:
            franchise.franchise_status = "Active"

        franchise.save()

        return JsonResponse({
            "success": True,
            "message": f"Franchise status changed to {franchise.franchise_status}",
            "status": franchise.franchise_status,
            "franchise_id": franchise.id
        })

    return JsonResponse({"success": False, "message": "Invalid request method!"}, status=400)



def franchise_basic_info(request,franchise_id=None):
    if not request.user.is_authenticated and request.user.is_active !=1 :
        messages.error(request,'Please Login First')
        return redirect('login')
    
    franchise= None
    if franchise_id:
        try:
            franchise= Franchise.objects.get(franchise_id=franchise_id)
        except Franchise.DoesNotExist:
            messages.error(request,"Invalid Franchise ID")
            return redirect('franchise-management-create')


    if request.method == 'POST':
        franchise_name =request.POST.get('franchise_name')
        franchise_type =request.POST.get('franchise_type')
        channel_type =request.POST.get('channel_type')
        franchise_status =request.POST.get('franchise_status')
        parent_broker_code =request.POST.get('parent_broker_code')
        onboarding_date =request.POST.get('onboarding_date')
        franchise_id =request.POST.get('franchise_id') or None
        franchise_code =request.POST.get('franchise_code') or None

        # if not franchise_id or not franchise_code:
        #     last_franchise = Franchise.objects.order_by('-id').first()
        #     next_id = 1 if not last_franchise else last_franchise.id + 1
        #     franchise_id = f"FID{next_id:05d}"
        #     franchise_code = f"FC{next_id:05d}"

        # # Basic validation
        # if not franchise_name or not franchise_type or not channel_type or not status:
        #     messages.error(request, 'Please fill in all required fields')
        #     return redirect('franchise-management-create') 

        if franchise:
            franchise.franchise_name = franchise_name
            franchise.franchise_type = franchise_type
            franchise.channel_type = channel_type
            franchise.franchise_status = franchise_status
            franchise.parent_broker_code = parent_broker_code
            franchise.onboarding_date = onboarding_date or timezone.now().date()
            franchise.save()
            messages.success(request,'Franchise updated sucessfully')
        else:
            last_franchise = Franchise.objects.order_by('-id').first()
            next_id = 1 if not last_franchise else last_franchise.id + 1
            franchise_id = f"FID{next_id:05d}"
            franchise_code = f"FC{next_id:05d}"
   
             # Save to DB
            franchise = Franchise.objects.create(
                franchise_id=franchise_id,
                franchise_code=franchise_code,
                franchise_name=franchise_name,
                franchise_type=franchise_type,
                channel_type=channel_type,
                franchise_status=franchise_status,
                parent_broker_code=parent_broker_code,
                onboarding_date=onboarding_date if onboarding_date else timezone.now().date()
            )  
            messages.success(request, 'Franchise added successfully')

        return redirect('franchise-management-contact-info', franchise_id=franchise.franchise_id) 
    
    return render(request, 'franchises/create-basic-detail.html',{ 
        'franchise':franchise,
        'franchise_id':franchise_id
    })

def franchise_contact_info(request,franchise_id=None):
    if not request.user.is_authenticated and request.user.is_active !=1 :
        messages.error(request,'Please Login First')
        return redirect('login')
    
    franchise = None
    if franchise_id:
        try:
            franchise = Franchise.objects.get(franchise_id=franchise_id)
        except Franchise.DoesNotExist:
            messages.error(request, "Invalid Franchise ID")
            return redirect('franchise-management-create')
    

    if request.method == 'POST':
        contact_person = request.POST.get('contact_person')
        mobile_number = request.POST.get('mobile_number')
        franchise_email = request.POST.get('email_address')
        alternate_number = request.POST.get('alternate_number')
        designation = request.POST.get('designation')

        # Save contact info (use your actual model name)
        if franchise:
            franchise.contact_person = contact_person
            franchise.mobile_number = mobile_number
            franchise.franchise_email = franchise_email
            franchise.alternate_number = alternate_number
            franchise.designation = designation
            franchise.save()
            messages.success(request, 'Contact Information updated successfully')
        else:
            messages.error(request, "Franchise not found to update contact info")
            return redirect('franchise-management-create')
        
        return redirect('franchise-management-address-details', franchise_id=franchise_id)  # Step 3

    return render(request, 'franchises/create-contact-info.html', {
        'franchise_id': franchise_id,
        'franchise_code': franchise.franchise_code if franchise else '',
        'franchise': franchise,
    })
        

def franchise_address_details(request, franchise_id=None):
    if not request.user.is_authenticated or request.user.is_active != 1:
        messages.error(request, 'Please Login First')
        return redirect('login')
    
    franchise = None
    if franchise_id:
        try:
            franchise = Franchise.objects.get(franchise_id=franchise_id)
        except Franchise.DoesNotExist:
            messages.error(request, "Invalid Franchise ID")
            return redirect('franchise-management-create')

    if request.method == 'POST':
        # get data from form
        franchise.address_line_1 = request.POST.get('address_line_1')
        franchise.address_line_2 = request.POST.get('address_line_2')
        franchise.city = request.POST.get('city')
        franchise.state = request.POST.get('state')
        franchise.pincode = request.POST.get('pincode')
        franchise.country = request.POST.get('country')
        franchise.office_contact_number = request.POST.get('office_contact_number')

        if franchise:
            franchise.address_line_1 = request.POST.get('address_line_1')
            franchise.address_line_2 = request.POST.get('address_line_2')
            franchise.city = request.POST.get('city')
            franchise.state = request.POST.get('state')
            franchise.pincode = request.POST.get('pincode')
            franchise.country = request.POST.get('country')
            franchise.office_contact_number = request.POST.get('office_contact_number')

            franchise.save()
            messages.success(request, 'Address Details Saved')
            return redirect('franchise-management-regulatory-compliance', franchise_id=franchise_id)
        else:
            messages.error(request, "Franchise not found to update address details")
            return redirect('franchise-management-create')

    return render(request, 'franchises/create-address-detail.html', {
        'franchise': franchise,
        'franchise_id': franchise_id,
    })

def franchise_regulatory_compliance(request, franchise_id=None):
    if not request.user.is_authenticated or request.user.is_active != 1:
        messages.error(request, 'Please Login First')
        return redirect('login')

    # franchise = get_object_or_404(Franchise, franchise_id=franchise_id)
    franchise = None
    if franchise_id:
        try:
            franchise = Franchise.objects.get(franchise_id=franchise_id)
        except Franchise.DoesNotExist:
            messages.error(request, "Invalid Franchise ID")
            return redirect('franchise-management-create')

    if request.method == 'POST':
        franchise.pan_number = request.POST.get('pan_number')
        franchise.gst_number = request.POST.get('gst_number')
        franchise.aadhar_number = request.POST.get('aadhar_number')

        if franchise:
            franchise.pan_number = request.POST.get('pan_number')
            franchise.gst_number = request.POST.get('gst_number')
            franchise.aadhar_number = request.POST.get('aadhar_number')
            franchise.save()
            messages.success(request, 'Regulatory & Compliance Details Saved')
            return redirect('franchise-management-banking-details', franchise_id=franchise_id)
        else:
            messages.error(request, "Franchise not found to update regulatory compliance details")
            return redirect('franchise-management-create')

    return render(request, 'franchises/create-regulatory-compliance.html', {
        'franchise': franchise,
        'franchise_id': franchise_id,
    })

def franchise_banking_details(request, franchise_id=None):
    if not request.user.is_authenticated or request.user.is_active != 1:
        messages.error(request, 'Please Login First')
        return redirect('login')
    
    franchise = None
    if franchise_id:
        try:
            franchise = Franchise.objects.get(franchise_id=franchise_id)
        except Franchise.DoesNotExist:
            messages.error(request, "Invalid Franchise ID")
            return redirect('franchise-management-create')

    if request.method == 'POST':
        franchise.account_holder_name = request.POST.get('account_holder_name')
        franchise.bank_name           = request.POST.get('bank_name')
        franchise.account_number      = request.POST.get('account_number')
        franchise.ifsc_code           = request.POST.get('ifsc_code')
        franchise.upi_id              = request.POST.get('upi_id')
        franchise.payment_mode        = request.POST.get('payment_mode')


        if franchise:
            franchise.account_holder_name = request.POST.get('account_holder_name')
            franchise.bank_name = request.POST.get('bank_name')
            franchise.account_number = request.POST.get('account_number')
            franchise.ifsc_code = request.POST.get('ifsc_code')
            franchise.upi_id = request.POST.get('upi_id')
            franchise.payment_mode = request.POST.get('payment_mode')
            franchise.save()
            messages.success(request, 'Banking & Payout Details Saved')
            return redirect('franchise-management')
        else:
            messages.error(request, "Franchise not found to update banking details")
            return redirect('franchise-management-create')

    return render(request, 'franchises/create-banking-detail.html', {
        'franchise': franchise,
        'franchise_id': franchise_id,
    })