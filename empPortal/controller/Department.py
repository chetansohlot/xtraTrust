from django.shortcuts import render,redirect, get_object_or_404
from ..models import Franchises, Department
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
from django.core.paginator import Paginator
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

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
    sort_by = request.GET.get('sort_by','') # Sort Criteria 

    try:
        per_page = int(per_page)
    except ValueError:
        per_page = 10  # Default to 10 if an invalid value is given

    departments = Department.objects.all().order_by('-created_at')

    # Apply filtering
    if search_field and search_query:
        filter_args = {f"{search_field}__icontains": search_query}
        departments = departments.filter(**filter_args)

    ### Sort Criteria ###
    if sort_by == 'name-a_z':
        departments = departments.order_by('name')
    elif sort_by == 'name-z_a':
        departments = departments.order_by('-name')
    elif sort_by == 'recently_activated':
        departments = departments.order_by('-created_at')
    elif sort_by == 'recently_deactivated':
        departments = departments.order_by('updated_at') 
    else :
        departments = departments.order_by('-created_at')  ##  default Sort     

    total_count = departments.count()

    # Pagination
    paginator = Paginator(departments, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'department/index.html', {
        'page_obj': page_obj, 
        'total_count': total_count,
        'search_field': search_field,
        'search_query': search_query,
        'per_page': per_page,
        'sort_by' : sort_by,   ## Sort Criteria
    })



def create_or_edit(request, department_id=None):
    if not request.user.is_authenticated:
        return redirect('login')

    # Fetch existing department if editing
    department = None
    if department_id:
        department = get_object_or_404(Department, id=department_id)

    if request.method == "GET":
        return render(request, 'department/create.html', {
            'department': department  # Pass existing data if editing
        })
    
    elif request.method == "POST":
        # Extract form data
        name = request.POST.get("name", "").strip()
        mobile = request.POST.get("mobile", "").strip()

        if department:
            # Update existing department
            department.name = name
            # department.contact_number = mobile
            # department.email = email
            # department.department_code = department_code
            department.updated_at = now()
            department.save()

            messages.success(request, f"Department updated successfully! Department ID: {department.id}")
            return redirect(reverse("department-management"))  # Redirect to department listing

        else:
            # Create new department
            new_department = Department.objects.create(
                name=name,
                # contact_number=mobile,
                # email=email,
                # department_code=department_code,  # New Field
                created_at=now(),
                updated_at=now(),
            )

            messages.success(request, f"Department created successfully! Department ID: {new_department.id}")
            return redirect(reverse("department-management"))  

#Anjali
def toggle_department_status(request, department_id):
    """Toggle department status based on user action (Activate/Deactivate)"""
    if request.method == "POST":
        department = get_object_or_404(Department, id=department_id)
        
        # Toggle status
        if department.status == "Active":
            department.status = "Inactive"
        else:
            department.status = "Active"

        department.save()

        return JsonResponse({
            "success": True,
            "message": f"Department status updated to {department.status}",
            "status": department.status,
            "department_id": department.id
        })

    return JsonResponse({"success": False, "message": "Invalid request method!"}, status=400)