from django.shortcuts import render,redirect, get_object_or_404
from ..models import Franchises, Branch, Department, Users, Roles
from django.db.models import OuterRef, Subquery
from django.contrib import messages
from datetime import datetime
from django.urls import reverse
import pprint  # Import pprint for better formatting
from django.http import JsonResponse
import pdfkit
from empPortal.model import Partner
import os
from ..model import State, City

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
from django.contrib.auth.hashers import make_password
import re
from django.http import JsonResponse
from empPortal.model import EmployeeDetails

from empPortal.model import Employees
from empPortal.model import Address
from empPortal.model import FamilyDetail
from empPortal.model import EmploymentInfo
from empPortal.model import EmployeeReference
from django.utils import timezone
import logging
from django.db.models import Q

from datetime import date

from empPortal.model import XtClientsBasicInfo
def dictfetchall(cursor):
    "Returns all rows from a cursor as a dict"
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


from django.db.models import Exists, OuterRef

def index(request):
    if not request.user.is_authenticated:
        return redirect('login')

    per_page = request.GET.get('per_page', 10)
    search_field = request.GET.get('search_field', '')
    search_query = request.GET.get('search_query', '')
    sort_by = request.GET.get('sort_by', '')  # Sort Criteria

    try:
        per_page = int(per_page)
    except ValueError:
        per_page = 10  

    # Fetch all users with associated employees, ensuring only those with employees are included
    users_with_employees = Users.objects.annotate(
        has_employee=Exists(Employees.objects.filter(user_id=OuterRef('id')))
    ).filter(has_employee=True, status=1).exclude(role_id__in=[1, 4])

    # Apply filtering if search query is provided
    if search_field and search_query:
        filter_args = {f"{search_field}__icontains": search_query}
        users_with_employees = users_with_employees.filter(**filter_args)

    # Sort Criteria
    if sort_by == 'name-a_z':
        users_with_employees = users_with_employees.order_by('first_name')
    elif sort_by == 'name-z_a':
        users_with_employees = users_with_employees.order_by('-first_name')
    elif sort_by == 'recently_activated':
        users_with_employees = users_with_employees.order_by('-created_at')  # latest first
    elif sort_by == 'recently_deactivated':
        users_with_employees = users_with_employees.order_by('-updated_at')  # Latest Updated first
    else:
        users_with_employees = users_with_employees.order_by('-created_at')  # Default Sorting  

    total_count = users_with_employees.count()

    # Fetch branch names separately
    branches = {str(branch.id): branch.branch_name for branch in Branch.objects.all()}

    # Fetch all users in a dictionary for supervisor lookup
    all_users = {str(user.id): user for user in Users.objects.all()}

    # Pagination
    paginator = Paginator(users_with_employees, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'employee/index.html', {
        'page_obj': page_obj, 
        'total_count': total_count,
        'search_field': search_field,
        'search_query': search_query,
        'per_page': per_page,
        'branches': branches,
        'all_users': all_users,  # Pass all users for supervisor lookup
        'sort_by': sort_by,  ## Sort Criteria
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


def save_or_update_employee(request, employee_id=None):
    if not request.user.is_authenticated and request.user.is_active != 1:
        # messages.error
        return redirect('login')

    # user_instance = None
    employee_instance = None

    if employee_id:
        # user_instance = get_object_or_404(Users, id=employee_id)
        employee_instance = get_object_or_404(Employees, employee_id=employee_id)

    if request.user.role_id != 1:
        messages.error(request, "You do not have permission to add or edit employees.")
        return redirect('employee-management')

    if request.method == "POST":
        pan_no = request.POST.get("pan_no", "").strip()
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        email = request.POST.get("email", "").strip()
        phone = request.POST.get("phone", "").strip()
        password = request.POST.get("password", "").strip()

        dob = request.POST.get("dob", "").strip()
        gender = request.POST.get("gender", "").strip()
        blood_group = request.POST.get("blood_group", "").strip()
        marital_status = request.POST.get("marital_status", "").strip()
        aadhaar_card = request.POST.get("aadhaar_card", "").strip()
        client = request.POST.get("client", "").strip()

        # Populate employee data for repopulating form in case of errors
        employee_data = {
            'first_name': first_name,
            'last_name': last_name,
            'dob': dob,
            'gender': gender,
            'pan_card': pan_no,
            'aadhaar_card': aadhaar_card,
            'mobile_number': phone,
            'email_address': email,
            'blood_group': blood_group,
            'marital_status': marital_status,
        }

        try:
            dob_date = datetime.strptime(dob, "%Y-%m-%d").date() if dob else None
        except ValueError:
            messages.error(request, "Invalid date format in DOB field.")
            return render(request, 'employee/create.html', {
                'employee': employee_data,
                # 'user': user_instance
            })

        today = date.today()
        if dob_date and (today.year - dob_date.year - ((today.month, today.day) < (dob_date.month, dob_date.day))) < 18:
            messages.error(request, "Employee must be at least 18 years old.")
            return render(request, 'employee/create.html', {
                'employee': employee_data,
                # 'user': user_instance
            })

        gender_map = {'Male': 1, 'Female': 2, 'Other': 3}
        user_gender = gender_map.get(gender, None)

        if not first_name or not email or not phone or not dob_date or not gender or not pan_no:
            messages.error(request, "Please fill all required fields.")
            return render(request, 'employee/create.html', {
                'employee': employee_data,
                # 'user': user_instance
            })

        # Check for duplicate Users
        # duplicate_user = Users.objects.filter(
        #     Q(email=email) | Q(phone=phone) | Q(pan_no=pan_no)
        # ).exclude(id=user_instance.id if user_instance else None).first()

        # if duplicate_user:
        #     if duplicate_user.email == email:
        #         messages.error(request, "Email already exists.")
        #     elif duplicate_user.phone == phone:
        #         messages.error(request, "Phone number already exists.")
        #     elif duplicate_user.pan_no == pan_no:
        #         messages.error(request, "PAN number already exists.")
        #     return render(request, 'employee/create.html', {
        #         'employee': employee_data,
        #         # 'user': user_instance
        #     })

        # Check for duplicate Employees
        duplicate_employee = Employees.objects.filter(
            Q(aadhaar_card=aadhaar_card))
        # ).exclude(user_id=user_instance.id if user_instance else None).first()

        if duplicate_employee:
            messages.error(request, "Aadhaar number already exists.")
            return render(request, 'employee/create.html', {
                'employee': employee_data,
                # 'user': user_instance
            })

        # Save or update Users table
        # if user_instance:
        #     user_instance.first_name = first_name
        #     user_instance.last_name = last_name
        #     user_instance.email = email
        #     user_instance.phone = phone
        #     user_instance.pan_no = pan_no
        #     user_instance.dob = dob
        #     user_instance.gender = user_gender
        #     user_instance.updated_at = timezone.now()
        #     if password:
        #         user_instance.password = make_password(password)
        #     user_instance.save()
        # else:
        #     last_user = Users.objects.order_by('-id').first()
        #     new_gen_id = "UR-0001"
        #     if last_user and last_user.user_gen_id.startswith('UR-'):
        #         last_num = int(last_user.user_gen_id.split('-')[1])
        #         new_gen_id = f"UR-{last_num+1:04d}"

        #     user_instance = Users.objects.create(
        #         user_gen_id=new_gen_id,
        #         first_name=first_name,
        #         last_name=last_name,
        #         email=email,
        #         phone=phone,
        #         pan_no=pan_no,
        #         dob=dob,
        #         gender=user_gender,
        #         password=make_password(password),
        #         status=1,
        #         created_at=timezone.now()
        #     )

        # Save or update Employees table
        employee_obj, created = Employees.objects.get_or_create(employee_id=employee_id)
        employee_obj.first_name = first_name
        employee_obj.last_name = last_name
        employee_obj.date_of_birth = dob_date
        employee_obj.gender = gender
        employee_obj.pan_card = pan_no
        employee_obj.aadhaar_card = aadhaar_card
        employee_obj.mobile_number = str(phone)
        employee_obj.email_address = email
        employee_obj.blood_group = blood_group
        employee_obj.marital_status = marital_status
        employee_obj.client_id = client
        employee_obj.updated_at = timezone.now()
        if created:
            employee_obj.created_at = timezone.now()
        employee_obj.save()

        messages.success(request, f"Employee {'created' if created else 'updated'} successfully!")
        return redirect('employee-management-update-address', employee_id=employee_obj.employee_id)

    else:
        clients_list = XtClientsBasicInfo.objects.filter(active='active')
        return render(request, 'employee/create.html', {
            'employee': employee_instance,
            'clients_list':clients_list
            # 'user': user_instance
        })

def view_employee(request, employee_id):
    try:
        user = get_object_or_404(Users, id=employee_id)
        employee = get_object_or_404(Employees, user_id=employee_id)

        # Fetch addresses
        permanent_address = Address.objects.filter(employee_id=employee.employee_id, type='Permanent').first()
        correspondence_address = Address.objects.filter(employee_id=employee.employee_id, type='Correspondence').first()

        # Family members
        family_members = FamilyDetail.objects.filter(employee_id=employee.employee_id)

        # Employment info
        employment_info = EmploymentInfo.objects.filter(employee_id=employee.employee_id).first()

        # References
        references = EmployeeReference.objects.filter(employee_id=employee.employee_id)

        # Fetch manager user
        manager_details = None
        if user.department_id:
            # Assuming 'manager' is the senior or manager related by senior_id or some other logic
            try:
                manager_details = Users.objects.get(id=user.senior_id)  # or user.manager_id if you have that
            except Users.DoesNotExist:
                manager_details = None

        # Fetch team leader user
        senior_details = None
        if user.senior_id:
            try:
                senior_details = Users.objects.get(id=user.senior_id)
            except Users.DoesNotExist:
                senior_details = None

        if user.role_id == 7 or user.role_id == '7':
            try:
                manager_details = Users.objects.get(id=senior_details.senior_id)  # or user.manager_id if you have that
            except Users.DoesNotExist:
                manager_details = None

        context = {
            'employee': employee,
            'user': user,
            'permanent_address': permanent_address,
            'correspondence_address': correspondence_address,
            'family_members': family_members,
            'employment_info': employment_info,
            'references': references,
            'manager_details': manager_details,
            'senior_details': senior_details,
        }

        return render(request, 'employee/view-employee.html', context)

    except Exception as e:
        # Optionally log the exception e here
        return redirect('employee-management')


def save_or_update_address(request, employee_id):
    if not request.user.is_authenticated:
        return redirect('login')

    employee = get_object_or_404(Employees, employee_id=employee_id)

    if request.user.role_id != 1:
        messages.error(request, "You do not have permission to edit employee address.")
        return redirect('employee-management')

    if request.method == "POST":
        for address_type in ["permanent"]:
            addr = request.POST.get(f"{address_type}_address", "").strip()
            state = request.POST.get(f"{address_type}_state", "").strip()
            city = request.POST.get(f"{address_type}_city", "").strip()
            pincode = request.POST.get(f"{address_type}_pincode", "").strip()

            # Basic validation
            if not addr:
                messages.error(request, f"{address_type.capitalize()} Address is required")
            if not state:
                messages.error(request, f"{address_type.capitalize()} State is required")
            if not city:
                messages.error(request, f"{address_type.capitalize()} City is required")
            if not pincode or not pincode.isdigit() or len(pincode) != 6:
                messages.error(request, f"Invalid {address_type.capitalize()} Pincode")

        if messages.get_messages(request):
            return redirect(request.META.get('HTTP_REFERER', '/'))

        for address_type in ["permanent", "correspondence"]:
            addr, state, city, pincode = (
                request.POST.get(f"{address_type}_address", "").strip(),
                request.POST.get(f"{address_type}_state", "").strip(),
                request.POST.get(f"{address_type}_city", "").strip(),
                request.POST.get(f"{address_type}_pincode", "").strip()
            )

            address_obj, created = Address.objects.get_or_create(
                employee_id=employee.employee_id, 
                type=address_type
            )
            address_obj.address = addr
            address_obj.state = state
            address_obj.city = city
            address_obj.pincode = pincode
            address_obj.updated_at = now()
            address_obj.active = True
            address_obj.save()

        messages.success(request, "Employee addresses updated successfully.")
        return redirect('employee-management-family-details', employee_id=employee.employee_id)

    # Pre-fill data
    permanent_address = Address.objects.filter(employee_id=employee.employee_id, type="permanent").first()
    correspondence_address = Address.objects.filter(employee_id=employee.employee_id, type="correspondence").first()

    states = State.objects.all()
    permanent_state = permanent_address.state if permanent_address else None
    correspondence_state = correspondence_address.state if correspondence_address else None

    # Get cities by state
    permanent_cities = City.objects.filter(state_id=permanent_state) if permanent_state else []
    correspondence_cities = City.objects.filter(state_id=correspondence_state) if correspondence_state else []

    return render(request, 'employee/create-address.html', {
        'employee': employee,
        'permanent': permanent_address,
        'states': states,
        'correspondence': correspondence_address,
        'permanent_cities': permanent_cities,
        'correspondence_cities': correspondence_cities
    })

def save_or_update_family_details(request, employee_id):
    if not request.user.is_authenticated:
        return redirect('login')

    if request.user.role_id != 1:
        messages.error(request, "You do not have permission to modify family details.")
        return redirect('employee-management')

    relations = ['Father', 'Mother', 'Spouse']
    
    if request.method == "POST":
        has_errors = False

        for relation in relations:
            first_name = request.POST.get(f"{relation.lower()}_first_name", "").strip()
            last_name = request.POST.get(f"{relation.lower()}_last_name", "").strip()
            dob = request.POST.get(f"{relation.lower()}_dob", "").strip()

            if not first_name or not last_name or not dob:
                continue  # Skip if any required field is missing

            try:
                dob_date = datetime.strptime(dob, "%Y-%m-%d").date()
            except ValueError:
                messages.error(request, f"Invalid {relation} DOB format. Use YYYY-MM-DD")
                has_errors = True
                continue

            # Validate age for Father and Mother
            if relation in ['Father', 'Mother']:
                today = date.today()
                age = today.year - dob_date.year - ((today.month, today.day) < (dob_date.month, dob_date.day))
                if age < 18:
                    messages.error(request, f"{relation} must be at least 18 years old.")
                    has_errors = True
                    continue

            # Create or update FamilyDetail
            family_record, created = FamilyDetail.objects.get_or_create(
                employee_id=employee_id,
                relation=relation,
                defaults={
                    'first_name': first_name,
                    'last_name': last_name,
                    'date_of_birth': dob_date,
                    'active': True
                }
            )
            if not created:
                family_record.first_name = first_name
                family_record.last_name = last_name
                family_record.date_of_birth = dob_date
                family_record.active = True
                family_record.save()

        if has_errors:
            # Return form with POST data on error
            family_data = {}
            for relation in relations:
                family_data[relation] = {
                    'first_name': request.POST.get(f"{relation.lower()}_first_name", "").strip(),
                    'last_name': request.POST.get(f"{relation.lower()}_last_name", "").strip(),
                    'date_of_birth': request.POST.get(f"{relation.lower()}_dob", "").strip(),
                }

            employee = get_object_or_404(Employees, employee_id=employee_id)
            return render(request, 'employee/create-family-details.html', {
                'employee_id': employee_id,
                'employee': employee,
                'family': family_data
            })

        messages.success(request, f"Family details updated for Employee ID: {employee_id}")
        return redirect('employee-management-employment-info', employee_id=employee_id)

    # GET request - Preload family data
    employee = get_object_or_404(Employees, employee_id=employee_id)
    family_qs = FamilyDetail.objects.filter(employee_id=employee_id, active=True)
    family_data = {}

    for relation in relations:
        record = next((f for f in family_qs if f.relation == relation), None)
        if record:
            family_data[relation] = {
                'first_name': record.first_name,
                'last_name': record.last_name,
                'date_of_birth': record.date_of_birth.strftime("%Y-%m-%d") if record.date_of_birth else ''
            }
        else:
            family_data[relation] = {'first_name': '', 'last_name': '', 'date_of_birth': ''}

    return render(request, 'employee/create-family-details.html', {
        'employee_id': employee_id,
        'employee': employee,
        'family': family_data
    })




def save_or_update_employment_info(request, employee_id):
    if not request.user.is_authenticated:
        return redirect('login')
    company_emp = settings.COMPANY_EMP
    if request.user.role_id != 1:
        messages.error(request, "You do not have permission to update employment info.")
        return redirect('employee-management')

    # Try to get existing employment info or initialize a new one
    employment, created = EmploymentInfo.objects.get_or_create(employee_id=employee_id)

    if request.method == "POST":
        department = request.POST.get("department", "").strip()
        date_of_joining = request.POST.get("date_of_joining", "").strip()

        if date_of_joining:
            try:
                doj = datetime.strptime(date_of_joining, "%Y-%m-%d").date()
            except ValueError:
                messages.error(request, "Invalid Date of Joining. Use format YYYY-MM-DD.")
                return redirect(request.META.get('HTTP_REFERER', '/'))
        else:
            doj = None
        
        employee_code = f"{company_emp}-{10000 + int(employee_id)}"

        # Update model fields
        employment.employee_code = employee_code
        employment.designation = department  # Assuming 'department' maps to 'designation'
        employment.date_of_joining = doj
        employment.save()

        messages.success(request, "Employment information updated successfully.")
        return redirect('employee-management-update-refrences', employee_id=employee_id)

    employment_code = f"{company_emp}-{10000 + int(employee_id)}"

    return render(request, 'employee/create-employee-info.html', {'employment': employment, 'employee_id': employee_id, 'employment_code': employment_code })



def toggle_employee_status(request, employee_id, action):
    employee = get_object_or_404(Users, id=employee_id)

    if action == 'activate':
        employee.user_active = 1
        messages.success(request, "Employee activated successfully.")
    elif action in ['deactivate', 'delete']:
        employee.user_active = 0
        print(f"Employee ID: {employee_id} deactivated")
        messages.success(request, "Employee deactivated successfully.")
    else:
        messages.error(request, "Invalid action.")
        return redirect('employee-management')

    employee.save()
    return redirect('employee-management')

def save_or_update_refrences(request, employee_id):
    if not request.user.is_authenticated:
        return redirect('login')

    if request.user.role_id != 1:
        messages.error(request, "You do not have permission to modify references.")
        return redirect('employee-management')

    if request.method == "POST":
        # Reference 1
        ref1_data = {
            'relation': request.POST.get("reference1_relation_type", "").strip(),
            'first_name': request.POST.get("reference1_first_name", "").strip(),
            'last_name': request.POST.get("reference1_last_name", "").strip(),
            'mobile_number': request.POST.get("reference1_mobile_number", "").strip(),
            'email_address': request.POST.get("reference1_email_address", "").strip(),
        }

        # Reference 2
        ref2_data = {
            'relation': request.POST.get("reference2_relation_type", "").strip(),
            'first_name': request.POST.get("reference2_first_name", "").strip(),
            'last_name': request.POST.get("reference2_last_name", "").strip(),
            'mobile_number': request.POST.get("reference2_mobile_number", "").strip(),
            'email_address': request.POST.get("reference2_email_address", "").strip(),
        }

        if ref1_data['relation']:
            EmployeeReference.objects.update_or_create(
                employee_id=employee_id,
                relation=ref1_data['relation'],
                defaults={**ref1_data, 'employee_id': employee_id}
            )

        if ref2_data['relation']:
            EmployeeReference.objects.update_or_create(
                employee_id=employee_id,
                relation=ref2_data['relation'],
                defaults={**ref2_data, 'employee_id': employee_id}
            )

        messages.success(request, f"References updated for Employee ID: {employee_id}")
        employee_instance = get_object_or_404(Employees, employee_id=employee_id)
        return redirect('employee-management-update-allocation', employee_id=employee_instance.user_id)

    # GET request – fetch references by order (or relation name if preferred)
    references = EmployeeReference.objects.filter(employee_id=employee_id, active=True).order_by('reference_id')
    reference1 = references[0] if references.count() > 0 else None
    reference2 = references[1] if references.count() > 1 else None

    relation_choices = ["Husband", "Wife", "Son", "Daughter"]

    context = {
        'employee_id': employee_id,
        'reference1': reference1,
        'reference2': reference2,
        'relation_choices': relation_choices,
    }

    return render(request, 'employee/create-reference.html', context)

def create_or_edit(request, employee_id=None):
    if not request.user.is_authenticated:
        return redirect('login')

    employee = None
    if employee_id:
        employee = get_object_or_404(Users, id=employee_id)

    # Only allow admins to add/edit users
    if request.user.role_id != 1:
        messages.error(request, "You do not have permission to add or edit users.")
        return redirect('employee-management')

    roles = Roles.objects.exclude(id__in=[1, 4])  # Exclude roles with ID 1 and 4
    branches = Branch.objects.all().order_by('-created_at')
    departments = Department.objects.all().order_by('-created_at')

    user_instance = None
    if employee_id:
        user_instance = get_object_or_404(Users, id=employee_id)

    if request.method == "GET":
        return render(request, 'employee/create.html', {
            'roles': roles,
            'branches': branches,
            'employee': employee,
            'departments': departments,
            'user_instance': user_instance
        })

    elif request.method == "POST":
        pan_no = request.POST.get("pan_no", "").strip()
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        email = request.POST.get("email", "").strip()
        phone = request.POST.get("phone", "").strip()
        password = request.POST.get("password", "").strip()

        # Validations
        if not first_name:
            messages.error(request, 'First Name is required')
        elif len(first_name) < 3:
            messages.error(request, 'First Name must be at least 3 characters long')

        if last_name and len(last_name) < 3:
            messages.error(request, 'Last Name must be at least 3 characters long')

        if not email:
            messages.error(request, 'Email is required')
        elif not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
            messages.error(request, 'Invalid email format')
        elif not user_instance and Users.objects.filter(email=email).exists():
            messages.error(request, 'This email is already in use')

        if not phone:
            messages.error(request, 'Mobile No is required')
        elif not phone.isdigit() or len(phone) != 10 or phone[0] <= '5':
            messages.error(request, 'Invalid mobile number format')
        elif not user_instance and Users.objects.filter(phone=phone).exists():
            messages.error(request, 'This mobile number already exists.')

        if not password and not user_instance:
            messages.error(request, 'Password is required for new users')
        elif password and len(password) < 6:
            messages.error(request, 'Password must be at least 6 characters long')

        if messages.get_messages(request):
            return redirect(request.META.get('HTTP_REFERER', '/'))

        if user_instance:
            user_instance.first_name = first_name
            user_instance.last_name = last_name
            user_instance.email = email
            user_instance.phone = phone
            user_instance.pan_no = pan_no
            if password:
                user_instance.password = make_password(password)
            user_instance.save()

            messages.success(request, f"User updated successfully! User ID: {user_instance.id}")
            return redirect('employee-allocation-update', employee_id=user_instance.id)

        else:
            # Generate user_gen_id
            last_user = Users.objects.all().order_by('-id').first()
            if last_user and last_user.user_gen_id.startswith('UR-'):
                last_user_gen_id = int(last_user.user_gen_id.split('-')[1])
                new_gen_id = f"UR-{last_user_gen_id+1:04d}"
            else:
                new_gen_id = "UR-0001"

            new_user = Users.objects.create(
                user_gen_id=new_gen_id,
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                pan_no=pan_no,
                status=1,
                password=make_password(password),
                created_at=now(),
                updated_at=now(),
            )

            messages.success(request, f"User created successfully! User ID: {new_user.id}")
            return redirect('employee-allocation-update', employee_id=new_user.id)

def create_or_edit_allocation(request, employee_id=None):
    if not request.user.is_authenticated:
        return redirect('login')

    if request.method == "POST":
        department_id = request.POST.get('department', '').strip()
        branch_id = request.POST.get('branch', '').strip()
        role_id = request.POST.get('role', '').strip()
        senior_id = request.POST.get('senior', '').strip()
        team_leader = request.POST.get('team_leader', '').strip()
        team_leader_insert = request.POST.get('team_leader_insert', '').strip()

        has_error = False

        # Validate required fields
        if not department_id:
            messages.error(request, 'Department is required.')
            has_error = True
        if not branch_id:
            messages.error(request, 'Branch is required.')
            has_error = True
        if not role_id:
            messages.error(request, 'Role is required.')
            has_error = True

        # Prevent assigning the Admin role
        if role_id == '1':
            messages.error(request, "You cannot assign the Admin role.")
            has_error = True

        # Role-based validation
        if role_id == '5':
            if not team_leader:
                messages.error(request, "Manager selection is required for Role 5.")
                has_error = True
            else:
                senior_id = team_leader

        elif role_id == '6':
            if not team_leader_insert:
                messages.error(request, "Team Leader selection is required for Role 6.")
                has_error = True
            else:
                senior_id = team_leader_insert

        if has_error:
            return redirect(request.META.get('HTTP_REFERER', '/'))

        # Fetch user for update
        user_data = Users.objects.filter(id=employee_id).first()
        if user_data:
            user_data.department_id = department_id
            user_data.branch_id = branch_id
            user_data.role_id = role_id
            user_data.senior_id = senior_id
            user_data.save()
            messages.success(request, "User allocation updated successfully.")
        else:
            messages.error(request, "User not found.")

        return redirect('employee-management')

    # GET method - Load data for the allocation form
    departments = Department.objects.all().order_by('name')
    branches = Branch.objects.filter(status='Active').order_by('-created_at')
    roles = Roles.objects.exclude(id__in=[1, 4])
    senior_users = Users.objects.filter(role_id=2).values('id', 'first_name', 'last_name', 'senior_id')

    employee = Users.objects.filter(id=employee_id).first() if employee_id else None
    senior_details = None
    manager_list = []
    tl_list = []
    manager_id = None
    manager_details = None
    if employee:
        if employee.role_id == 5 and employee.senior_id:
            # Get TL details
            tl_details = Users.objects.filter(id=employee.senior_id).values('id', 'first_name', 'last_name', 'senior_id').first()
            if tl_details:
                senior_id = tl_details.get('senior_id')
                if senior_id:
                    senior_details = Users.objects.filter(id=senior_id).values('id', 'first_name', 'last_name').first()
                    manager_list = list(Users.objects.filter(senior_id=senior_id).values('id', 'first_name', 'last_name', 'role_id'))

        elif employee.role_id == 6 and employee.senior_id:
            # Get TL and their manager
            tl_details = Users.objects.filter(id=employee.senior_id).values('id', 'first_name', 'last_name', 'senior_id').first()
            if tl_details:
                manager_id = tl_details.get('senior_id')
                manager_details = Users.objects.filter(id=manager_id).values('id', 'first_name', 'last_name', 'senior_id').first()
                head_id = manager_details.get('senior_id')

                if manager_id:
                    tl_list = list(Users.objects.filter(senior_id=manager_id).values('id', 'first_name', 'last_name', 'role_id'))
                    manager_list = list(Users.objects.filter(senior_id=head_id).values('id', 'first_name', 'last_name', 'role_id'))
                    senior_details = Users.objects.filter(id=head_id).values('id', 'first_name', 'last_name').first()
                    print(manager_details)

        elif employee.senior_id:
            senior_details = Users.objects.filter(id=employee.senior_id).values('id', 'first_name', 'last_name', 'senior_id').first()

    return render(request, 'employee/allocation-update.html', {
        'employee': employee,
        'departments': departments,
        'branches': branches,
        'roles': roles,
        'senior_users': senior_users,
        'manager_id': manager_id,
        'manager_list': manager_list,
        'manager_details': manager_details,
        'tl_list': tl_list,
        'senior_details': senior_details,
    })


    
    
def update_allocation(request, employee_id=None):
    if not request.user.is_authenticated:
        return redirect('login')

    if request.method == "POST":
        department_id = request.POST.get('department', '').strip()
        branch_id = request.POST.get('branch', '').strip()
        role_id = request.POST.get('role', '').strip()
        senior_id = request.POST.get('senior', '').strip()
        team_leader = request.POST.get('manager', '').strip()
        team_leader_insert = request.POST.get('team_leader', '').strip()
        is_branch_head = request.POST.get('is_branch_head', '0')
        annual_ctc = request.POST.get('annual_ctc', 0)
        monthly_ctc = request.POST.get('monthly_ctc', 0)
        target_percent = request.POST.get('target_percent', 0)
        target_amt = request.POST.get('target_amt', 0)
        monthly_target_amt = request.POST.get('monthly_target_amt', 0)

        has_error = False

        # Validation
        if not branch_id:
            messages.error(request, 'Branch is required.')
            has_error = True
            
        if not annual_ctc:
            messages.error(request, 'Annual CTC is required.')
            has_error = True
        elif len(str(annual_ctc)) > 16:
            messages.error(request, 'Annual CTC must be at most 16 characters long.')
            has_error = True
        else:
            try:
                float(annual_ctc)
            except ValueError:
                messages.error(request, 'Annual CTC must be a valid number.')
                has_error = True

        if not monthly_ctc:
            messages.error(request, 'Monthly CTC is required.')
            has_error = True
        elif len(str(monthly_ctc)) > 16:
            messages.error(request, 'Monthly CTC must be at most 16 digit long.')
            has_error = True
        else:
            try:
                float(monthly_ctc)
            except ValueError:
                messages.error(request, 'Monthly CTC must be a valid number.')
                has_error = True


        if not target_percent:
            messages.error(request, 'Target Percentage is required.')
            has_error = True
        elif len(str(target_percent))>5:
            messages.error(request, 'Target Percentage must be at most 4 characters long.')
            has_error = True
        else:
            try:
                float(target_percent)
            except ValueError:
                messages.error(request, 'Target Percentage must be a valid number.')
                has_error = True

        if not target_amt:
            messages.error(request, 'Target Amount is required.')
            has_error = True
        elif len(str(target_amt))>16:
            messages.error(request, 'Target Amount must be at most 16 characters long.')
            has_error = True
        else:
            try:
                float(target_amt)
            except ValueError:
                messages.error(request, 'Target Amount must be a valid number.')
                has_error = True
            
        if not monthly_target_amt:
            messages.error(request, 'Monthly Target Amount is required.')
            has_error = True
        elif len(str(monthly_target_amt))>16:
            messages.error(request, 'Monthly Target Amount must be at most 16 characters long.')
            has_error = True
        else:
            try:
                float(monthly_target_amt)
            except ValueError:
                messages.error(request, 'Monthly Target Amount must be a valid number.')
                has_error = True
            
        if not role_id and is_branch_head == '0':
            messages.error(request, 'Role is required.')
            has_error = True

        role_id_int = int(role_id) if role_id.isdigit() else 0

        if role_id_int > 4 and not department_id:
            messages.error(request, 'Department is required.')
            has_error = True

        if role_id == '1':
            messages.error(request, "You cannot assign the Admin role.")
            has_error = True

        if role_id == '6':  # Team Leader → needs Manager
            if not team_leader:
                messages.error(request, "Manager selection is required for Role 6 (Team Leader).")
                has_error = True
            else:
                senior_id = team_leader

        elif role_id == '7':  # RM → needs Team Leader
            if not team_leader_insert:
                messages.error(request, "Team Leader selection is required for Role 7 (Relationship Manager).")
                has_error = True
            else:
                senior_id = team_leader_insert

        if has_error:
            return redirect(request.META.get('HTTP_REFERER', '/'))

        # Save or update
        user_data = Users.objects.filter(id=employee_id).first()
        if user_data:
            user_data.department_id = department_id if role_id_int > 4 else None
            user_data.branch_id = branch_id
            user_data.role_id = role_id
            user_data.annual_ctc = annual_ctc
            user_data.monthly_ctc = monthly_ctc
            user_data.target_percent = target_percent
            user_data.target_amt = target_amt
            user_data.monthly_target_amt = monthly_target_amt
            user_data.senior_id = senior_id if senior_id else None
            user_data.branch_head = 1 if is_branch_head == '1' else 0
            user_data.save()
            messages.success(request, "User allocation updated successfully.")
        else:
            messages.error(request, "User not found.")

        return redirect('employee-management')

    # GET method: load form
    departments = Department.objects.all().order_by('name')
    branches = Branch.objects.filter(status='Active').order_by('-created_at')
    roles = Roles.objects.exclude(id__in=[1, 4])  # Exclude Admin and possibly Superuser
    employee = Users.objects.filter(id=employee_id).first() if employee_id else None

    senior_details = None
    manager_list = []
    tl_list = []
    manager_details = None
    manager_id = None

    if employee:
        if employee.role_id == 6 and employee.senior_id:
            # Team Leader: senior is Manager
            manager_user = Users.objects.filter(id=employee.senior_id).first()
            if manager_user:
                manager_list = Users.objects.filter(role_id=5, branch_id=employee.branch_id).values(
                    'id', 'first_name', 'last_name'
                )
                manager_details = manager_user
                manager_id = manager_user.id
                if manager_user.senior_id:
                    senior_details = Users.objects.filter(id=manager_user.senior_id).values(
                        'id', 'first_name', 'last_name'
                    ).first()

        elif employee.role_id == 7 and employee.senior_id:
            # RM: senior is TL, TL's senior is Manager
            tl_user = Users.objects.filter(id=employee.senior_id).first()
            if tl_user:
                tl_list = Users.objects.filter(role_id=6, senior_id=tl_user.senior_id).values(
                    'id', 'first_name', 'last_name'
                )
                if tl_user.senior_id:
                    manager_user = Users.objects.filter(id=tl_user.senior_id).first()
                    if manager_user:
                        manager_list = Users.objects.filter(role_id=5, branch_id=employee.branch_id).values(
                            'id', 'first_name', 'last_name'
                        )
                        manager_details = manager_user
                        manager_id = manager_user.id
                        if manager_user.senior_id:
                            senior_details = Users.objects.filter(id=manager_user.senior_id).values(
                                'id', 'first_name', 'last_name'
                            ).first()

        elif employee.senior_id:
            # Others: just get senior
            senior_details = Users.objects.filter(id=employee.senior_id).values(
                'id', 'first_name', 'last_name', 'senior_id'
            ).first()

    employee_instance = Employees.objects.filter(user_id=employee.id).first()
    return render(request, 'employee/create-allocation.html', {
        'employee': employee,
        'employee_data': employee_instance,
        'departments': departments,
        'branches': branches,
        'roles': roles,
        'senior_users': Users.objects.all().values('id', 'first_name', 'last_name'),
        'manager_id': manager_id,
        'manager_list': manager_list,
        'manager_details': manager_details,
        'tl_list': tl_list,
        'senior_details': senior_details,
    })
