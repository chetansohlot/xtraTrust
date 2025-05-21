from django.shortcuts import render,redirect, get_object_or_404
from ..models import Franchises, Branch
from django.db.models import OuterRef, Subquery
from django.contrib import messages
from datetime import datetime
from django.urls import reverse
import pprint  # Import pprint for better formatting
from django.http import JsonResponse
import pdfkit
# import os
from django.conf import settings
import os
from dotenv import load_dotenv
from django.templatetags.static import static  # ✅ Import static
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.forms.models import model_to_dict
import json
from django.utils.timezone import now
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
    search_field = request.GET.get('search_field', '')  # Field to search
    search_query = request.GET.get('search_query', '')  # Search value
    sort_by =request.GET.get('sort_by','')  # Sort Criteria ----parth

    try:
        per_page = int(per_page)
    except ValueError:
        per_page = 10  # Default to 10 if invalid value is given

    branches = Branch.objects.all().order_by('-created_at')

    # Apply filtering
    if search_field and search_query:
        filter_args = {f"{search_field}__icontains": search_query}
        branches = branches.filter(**filter_args)

    # Sort Criteria ----parth ####
    if sort_by == 'name-a_z':
        branches = branches.order_by('branch_name')
    elif sort_by == 'name-z_a':
        branches = branches.order_by('-branch_name')
    elif sort_by == 'recently_activated':
        branches = branches.order_by('-created_at')
    elif sort_by == 'recently_deactivated':
        branches = branches.order_by('-updated_at')
    else:
        branches = branches.order_by('-created_at')  # default sort  


    total_count = branches.count()

    # Pagination
    paginator = Paginator(branches, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'branches/index.html', {
        'page_obj': page_obj, 
        'total_count': total_count,
        'search_field': search_field,
        'search_query': search_query,
        'per_page': per_page,
        'sort_by': sort_by,  ## -----send back to templates for radio selected ratio --parth---
    })


def check_branch_email(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        branch_id = request.POST.get("branch_id", "").strip()
        
        print(f"Checking email: {email}, Branch ID: {branch_id}")  # Debugging

        # If editing, allow current branch email
        if branch_id:
            branch = Branch.objects.filter(id=branch_id).first()
            if branch and branch.email == email:
                return JsonResponse({"exists": False})  # Allow the current email

        # Check if email exists in any other branch
        exists = Branch.objects.filter(email=email).exists()
        print(f"Exists in DB: {exists}")  # Debugging

        return JsonResponse({"exists": exists})

    return JsonResponse({"error": "Invalid request"}, status=400)

def create_or_edit(request, branch_id=None):
    if not request.user.is_authenticated:
        return redirect('login')

    # Fetch existing branch if editing
    branch = None
    if branch_id:
        branch = get_object_or_404(Branch, id=branch_id)

    if request.method == "GET":
        return render(request, 'branches/create.html', {
            'branch': branch  # Pass existing data if editing
        })
    
    elif request.method == "POST":
        # Extract form data
        branch_name = request.POST.get("branch_name", "").strip()
        contact_person = request.POST.get("contact_person", "").strip()
        mobile = request.POST.get("mobile", "").strip()
        email = request.POST.get("email", "").strip()
        address = request.POST.get("address", "").strip()
        city = request.POST.get("city", "").strip()
        state = request.POST.get("state", "").strip()
        pincode = request.POST.get("pincode", "").strip()

        if branch:
            # Update existing record
            branch.branch_name = branch_name
            branch.contact_person = contact_person
            branch.mobile = mobile
            branch.email = email
            branch.address = address
            branch.city = city
            branch.state = state
            branch.pincode = pincode
            branch.updated_at = now()
            branch.save()

            messages.success(request, f"Branch updated successfully! Branch ID: {branch.id}")
            return redirect(reverse("branch-management"))  # Redirect to branch listing

        else:
            # Create new record
            new_branch = Branch.objects.create(
                branch_name=branch_name,
                contact_person=contact_person,
                mobile=mobile,
                email=email,
                address=address,
                city=city,
                state=state,
                pincode=pincode,
                created_at=now(),
                updated_at=now(),
            )

            messages.success(request, f"Branch created successfully! Branch ID: {new_branch.id}")
            return redirect(reverse("branch-management"))  # Redirect to branch listing
#Anjali
def toggle_branch_status(request, branch_id):
    if request.method == "POST":  
        branch = get_object_or_404(Branch, id=branch_id)
        action = request.POST.get("action")  
        print(f"Branch: {branch.branch_name}, Current Status: {branch.status}, Action: {action}")

        # Update status
        if action == "activate":
            branch.status = "Active"
        elif action == "deactivate":
            branch.status = "Inactive"
        else:
            return JsonResponse({'success': False, 'message': 'Invalid action!'}, status=400)

        branch.save()

        print(f"Updated Status in Database: {branch.status}")  

        return JsonResponse({'success': True, 'message': f"Branch status updated to {branch.status}", 'status': branch.status})

    return JsonResponse({'success': False, 'message': 'Invalid request method!'}, status=405)