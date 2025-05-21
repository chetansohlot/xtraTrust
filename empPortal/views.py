from django.http import HttpResponse
from django.contrib.auth.hashers import make_password
from django.contrib.auth import update_session_auth_hash
from django.shortcuts import render,redirect
from django.contrib import messages
from django.template import loader
from .models import Roles,Users, Department,PolicyDocument,BulkPolicyLog, PolicyInfo, Branch, UserFiles,UnprocessedPolicyFiles, Commission, Branch, FileAnalysis, ExtractedFile, ChatGPTLog
from django.contrib.auth import authenticate, login ,logout
from django.core.files.storage import FileSystemStorage
import re, logging
import requests
from fastapi import FastAPI, File, UploadFile
import fitz
import openai
import time
import json
from django.http import JsonResponse
import os
import zipfile
from django.conf import settings
from datetime import datetime
from io import BytesIO
from django.db.models import Q
from .models import UploadedZip
from django.core.files.base import ContentFile
from .tasks import process_zip_file
from django_q.tasks import async_task
from django.db.models import Sum
from django.utils import timezone
from django.utils.timezone import now
from empPortal.model import Referral
from urllib.parse import urljoin
from collections import Counter
from django.core.paginator import Paginator


OPENAI_API_KEY = settings.OPENAI_API_KEY
logging.getLogger('faker').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

app = FastAPI()

def billings(request):
    if request.user.is_authenticated:
        return render(request,'billings.html')
    else:
        return redirect('login')

def claimTracker(request):
    if request.user.is_authenticated:
        return render(request,'claim-tracker.html')
    else:
        return redirect('login')

def checkout(request):
    if request.user.is_authenticated:
        return render(request,'checkout.html')
    else:
        return redirect('login')

def addMember(request):
    if request.user.is_authenticated:
        return render(request,'add-member.html')
    else:
        return redirect('login')
    
def userAndRoles(request):
    if not request.user.is_authenticated:
        return redirect('login')
    
    roles = Roles.objects.exclude(id__in=[1, 4])
    departments = Department.objects.in_bulk(field_name='id')  # {id: Department}
    all_roles_dict = {str(role.id): role for role in Roles.objects.all()}  # {'2': <Roles object>}

    for role in roles:
        # Get department name
        dept_id = role.roleDepartment
        role.department_name = departments.get(int(dept_id)).name if dept_id and dept_id.isdigit() and int(dept_id) in departments else ''

        # Get primary role name
        primary_role_id = role.primaryRoleId
        role.primary_role_name = all_roles_dict.get(primary_role_id).roleName if primary_role_id in all_roles_dict else ''

    return render(request, 'user-and-roles.html', {
        'role_data': roles,
    })



def newRole(request):
    if request.user.is_authenticated:
        departments = Department.objects.all().order_by('name')
        roles = Roles.objects.exclude(id__in=[1, 4])
        return render(request, 'new-role.html', {
            'departments': departments,
            'roles': roles
        })
    else:
        return redirect('login')

def insertRole(request):
    if not request.user.is_authenticated:
        return redirect('login')

    departments = Department.objects.all().order_by('name')
    roles = Roles.objects.exclude(id__in=[1, 4])

    if request.method == "POST":
        role_name = request.POST.get('role_name', '').strip()
        role_id = request.POST.get('role_id', '').strip()

        # Validation
        
        
        if not role_name:
            messages.error(request, 'Role Name is required')
            return render(request, 'new-role.html', {
                'departments': departments,
                'roles': roles,
                'role_name': role_name,
            })


        if len(role_name) < 3:
            messages.error(request, 'Role name must be at least 3 characters long')
            return render(request, 'new-role.html', {
                'departments': departments,
                'roles': roles,
                'role_name': role_name,
            })

    

        if Roles.objects.filter(roleName__iexact=role_name).exists():
            messages.error(request, "Role name already exists.")
            return render(request, 'new-role.html', {
                'departments': departments,
                'roles': roles,
                'role_name': role_name,
            })


        # Generate roleGenID
        last_role = Roles.objects.all().order_by('-roleGenID').first()
        if last_role and last_role.roleGenID.startswith('RL-'):
            last_id = int(last_role.roleGenID.split('-')[1])
            new_roleGenID = f"RL-{last_id + 1:04d}"
        else:
            new_roleGenID = 'RL-0001'

        # Save new role with department ID
        rl = Roles(
            roleGenID=new_roleGenID,
            roleName=role_name,
            primaryRoleId=role_id, 
        )
        rl.save()

        messages.success(request, "Role added successfully.")
        return redirect('user-and-roles')

    messages.error(request, 'Invalid method')
    return render(request, 'new-role.html', {
        'departments': departments,
        'roles': roles
        })




def createUser(request):
    if request.user.is_authenticated:
        roles = Roles.objects.exclude(id__in=[1, 4])

        branches = Branch.objects.all().order_by('-created_at')
        departments = Department.objects.all().order_by('-created_at')
        return render(request,'create-user.html',{'role_data':roles, 'branches':branches, 'departments':departments})
    else:
        return redirect('login')

def get_users_by_role(request):
    if request.method == "GET" and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        role_id = request.GET.get('role_id', '')
        manager_id = request.GET.get('manager_id', '')

        if role_id and role_id.isdigit():
            role_id = int(role_id)

            if role_id == 3:  # Fetch Branch Managers
                users = Users.objects.filter(role_id=2).values('id', 'first_name', 'last_name')
                role_name = "Head"
            elif role_id == 5 and manager_id == '':  # Fetch Regional Managers
                users = Users.objects.filter(role_id=2).values('id', 'first_name', 'last_name')
                role_name = "Head"
            elif role_id == 6 and manager_id == '':  # Fetch Regional Managers
                users = Users.objects.filter(role_id=2).values('id', 'first_name', 'last_name')
                role_name = "Head"
            elif role_id == 5 and manager_id != '' and manager_id.isdigit():  # Fetch Team Leaders under selected Manager
                users = Users.objects.filter(senior_id=manager_id).values('id', 'first_name', 'last_name')
                role_name = "Manager"
            elif role_id == 6 and manager_id != '' and manager_id.isdigit():  # Fetch Team Leaders under selected Manager
                users = Users.objects.filter(senior_id=manager_id).values('id', 'first_name', 'last_name')
                role_name = "Team Leader"
            else:
                return JsonResponse({'users': []}, status=200)

            users_list = [
                {'id': user['id'], 'full_name': f"{user['first_name']} {user['last_name']} ({role_name})".strip()}
                for user in users
            ]
            return JsonResponse({'users': users_list}, status=200)

        return JsonResponse({'users': []}, status=200)

    return JsonResponse({'error': 'Invalid request'}, status=400)


def get_team_leaders_by_manager(request):
    if request.method == "GET" and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        manager_id = request.GET.get('manager_id')
        branch_id = request.GET.get('branch_id')
        department_id = request.GET.get('department_id')

        if manager_id and manager_id.isdigit():
            filters = {'senior_id': int(manager_id)}
            if branch_id and branch_id.isdigit():
                filters['branch_id'] = int(branch_id)
            if department_id and department_id.isdigit():
                filters['department_id'] = int(department_id)

            users = Users.objects.filter(**filters).values('id', 'first_name', 'last_name')
            role_name = "Team Leader"

            users_list = [
                {'id': user['id'], 'full_name': f"{user['first_name']} {user['last_name']} ({role_name})"}
                for user in users
            ]
            return JsonResponse({'users': users_list}, status=200)

        return JsonResponse({'users': []}, status=200)

    return JsonResponse({'error': 'Invalid request'}, status=400)

def get_users_by_role_id(request):
    if request.method == "GET" and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        role_id = request.GET.get('role_id')
        branch_id = request.GET.get('branch_id')
        department_id = request.GET.get('department_id')

        if role_id and role_id.isdigit():
            filters = {'role_id': int(role_id)}
            if branch_id and branch_id.isdigit():
                filters['branch_id'] = int(branch_id)
            if department_id and department_id.isdigit():
                filters['department_id'] = int(department_id)

            users = Users.objects.filter(**filters).values('id', 'first_name', 'last_name')
            role_name = "Manager"

            users_list = [
                {'id': user['id'], 'full_name': f"{user['first_name']} {user['last_name']} ({role_name})"}
                for user in users
            ]
            return JsonResponse({'users': users_list}, status=200)

        return JsonResponse({'users': []}, status=200)

    return JsonResponse({'error': 'Invalid request'}, status=400)


def get_pos_partners_by_bqp(request):
    if request.method == "GET" and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        bqp_id = request.GET.get('bqp_id', '')

        if bqp_id and bqp_id.isdigit():
            bqp_id = int(bqp_id)

            users = Users.objects.filter(bqp_id=bqp_id).values('id', 'first_name', 'last_name')
            users_list = [
                {'id': user['id'], 'full_name': f"{user['first_name']} {user['last_name']}".strip()}
                for user in users
            ]
            return JsonResponse({'users': users_list}, status=200)

        return JsonResponse({'users': []}, status=200)

    return JsonResponse({'error': 'Invalid request'}, status=400)

def insertUser(request):
    if request.user.is_authenticated:
        
        if request.user.role_id != 1:
            messages.error(request, "You do not have permission to add users.")
            return redirect('user-and-roles')  # Redirect unauthorized users
        
        if request.method == "POST":
            username = request.POST.get('username', '').strip()
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            user_email = request.POST.get('email', '').strip()
            user_phone = request.POST.get('phone', 0).strip()
            role = request.POST.get('role', '').strip()
            branch = request.POST.get('branch', '').strip()
            department = request.POST.get('department', '').strip()
            senior = request.POST.get('senior', '').strip()  # New senior field
            password = request.POST.get('password', '').strip()


            if role == '1':
                messages.error(request, "You cannot create a user with this role Admin.")
                return redirect(request.META.get('HTTP_REFERER', '/'))
            
            if not username:
                messages.error(request, 'Username is required')
            elif len(username) < 3:
                messages.error(request, 'Username must be at least 3 characters long')
            elif Users.objects.filter(user_name=username).exists():
                messages.error(request,'This username is already exist')

            if not first_name:
                messages.error(request, 'First Name is required')
            elif len(first_name) < 3:
                messages.error(request, 'First Name must be at least 3 characters long')
            if not branch or not branch.isdigit():
                messages.error(request, 'Valid Branch is required')

            if last_name and len(last_name) < 3:
                messages.error(request, 'Last Name must be at least 3 characters long')

            if not user_email:
                messages.error(request, 'Email is required')
            elif not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", user_email):
                messages.error(request, 'Invalid email format')
            elif Users.objects.filter(email=user_email).exists():
                messages.error(request,'This email is already exist')

            if not user_phone:
                messages.error(request, 'Mobile No is required')
            elif not user_phone.isdigit():
                messages.error(request, 'Mobile No must contain only numbers')
            elif user_phone[0] <= '5':
                messages.error(request, 'Mobile No must start with a number greater than 5')
            elif len(user_phone) != 10:
                messages.error(request,'Mobile No must be of 10 digits')
            elif Users.objects.filter(phone=user_phone).exists():
                messages.error(request, 'This mobile number already exists.')

            if not role:
                messages.error(request, 'Role is required')
                
            if not password:
                messages.error(request, 'Password is required')
            elif len(password) < 6:
                messages.error(request, 'Password must be at least 6 characters long')
            
            if messages.get_messages(request):
                return redirect(request.META.get('HTTP_REFERER', '/'))

            last_user = Users.objects.all().order_by('-id').first()
            if last_user and last_user.user_gen_id.startswith('UR-'):
                last_user_gen_id = int(last_user.user_gen_id.split('-')[1])
                new_gen_id = f"UR-{last_user_gen_id+1:04d}"
            else:
                new_gen_id = "UR-0001"
                
            role_data = Roles.objects.filter(id=role).first()
            role_name = role_data.roleName
            
            user_password = make_password(password)

            
            user_gen_id = new_gen_id
            user_role_id = role
            user_role_name = role_name
            user_name = username
            user_first_name = first_name
            user_last_name = last_name
            user_email = user_email
            user_phone = user_phone
            user_password = user_password
            branch_id = branch
            department_id = department
            senior_id = senior
            user_status = 1

            user = Users(
                user_gen_id=user_gen_id, 
                role_id=user_role_id, 
                role_name=user_role_name, 
                user_name=user_name, 
                first_name=user_first_name, 
                last_name=user_last_name, 
                email=user_email, 
                phone=user_phone, 
                branch_id=branch_id, 
                department_id=department_id, 
                senior_id=senior_id, 
                status=user_status, 
                password=user_password
            )
            user.save()
            
            messages.success(request, "User added successfully.")
            return redirect('user-and-roles')

        messages.error(request, 'Invalid URL')
        return redirect(request.META.get('HTTP_REFERER', '/'))
    else:
        return redirect('login')

def editRole(request,id):
    if request.user.is_authenticated:
        role_data = Roles.objects.filter(roleGenID=id).first()
        departments = Department.objects.all().order_by('name')
        roles = Roles.objects.exclude(id__in=[1, 4])

        return render(request,'edit-role.html',{
            'role_data':role_data,
            'roles':roles,
            'departments': departments
        })
    else:
        return redirect('login')
    
def editUser(request, id):
    if request.user.is_authenticated:
        role_data = Roles.objects.all()
        branches = Branch.objects.all().order_by('branch_name')
        departments = Department.objects.all().order_by('name')
        user_data = Users.objects.filter(user_gen_id=id).first()

        senior_users = []  # Default empty list
        if user_data and user_data.role_id == 3:  
            senior_users = Users.objects.filter(role_id=2).values('id', 'first_name', 'last_name')

        return render(request, 'edit-user.html', {
            'user_data': user_data,
            'role_data': role_data,
            'branches': branches,
            'departments': departments,
            'senior_users': senior_users
        })
    else:
        return redirect('login')

def updateRole(request):
    if not request.user.is_authenticated:
        return redirect('login')

    departments = Department.objects.all().order_by('name')
    roles = Roles.objects.exclude(id__in=[1, 4])

    if request.method == "POST":
        role_id = request.POST.get('role_id', '').strip()
        primary_role_id = request.POST.get('primary_role_id', '').strip()
        role_name = request.POST.get('role_name', '').strip()

        if not role_id:
            messages.error(request, 'Something went wrong. Kindly contact the administrator')
            return redirect(request.META.get('HTTP_REFERER', '/'))

        # Validation
        if not role_name:
            messages.error(request, 'Role Name is required')
      
        if len(role_name) < 3:
            messages.error(request, 'Role name must be at least 3 characters long')
      
        if Roles.objects.filter(roleName=role_name).exclude(id=role_id).exists():
            messages.error(request, "Role name already exists.")

        # If any error, re-render the form with previous input
        if messages.get_messages(request):
            role_data = Roles.objects.filter(id=role_id).first()
            return render(request, 'edit-role.html', {
                'departments': departments,
                'roles': roles,
                'role_data': role_data,
                'role_name': role_name,
            })

        # Update the role
        role_data = Roles.objects.filter(id=role_id).first()
        if role_data:
            role_data.roleName = role_name
            role_data.primaryRoleId = primary_role_id

            role_data.save()

            messages.success(request, 'Role updated successfully.')
            return redirect('user-and-roles')
        else:
            messages.error(request, 'No data found')
            return redirect(request.META.get('HTTP_REFERER', '/'))

    else:
        messages.error(request, 'Invalid request method')
        return redirect('user-and-roles')

   
def updateUser(request):
    if request.user.is_authenticated:
        if request.method == "POST":
            user_id = request.POST.get('user_id', '').strip()

            if not user_id:
                messages.error(request, 'Something Went Wrong. Kindly contact the administrator')

            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            role_id = request.POST.get('role', '').strip()
            branch_id = request.POST.get('branch', '').strip()
            department_id = request.POST.get('department', '').strip()
            senior_id = request.POST.get('senior', '').strip()

            if role_id == '1':
                messages.error(request, "You cannot update a user with this role Admin.")
                return redirect(request.META.get('HTTP_REFERER', '/'))
            
            if not first_name:
                messages.error(request, 'First Name is required')
            elif len(first_name) < 3:
                messages.error(request, 'First Name must be at least 3 characters long')

            if last_name and len(last_name) < 3:
                messages.error(request, 'Last Name must be at least 3 characters long')

            if not role_id:
                messages.error(request, 'Role is required')

            if not branch_id:
                messages.error(request, 'Branch is required')

            if messages.get_messages(request):
                return redirect(request.META.get('HTTP_REFERER', '/'))

            role_data = Roles.objects.filter(id=role_id).first()
            role_name = role_data.roleName if role_data else ''

            user_data = Users.objects.filter(id=user_id).first()

            if user_data is not None:
                user_data.role_id = role_id
                user_data.role_name = role_name
                user_data.first_name = first_name
                user_data.last_name = last_name
                user_data.branch_id = branch_id
                user_data.department_id = department_id
                user_data.senior_id = senior_id  # Update senior_id
                user_data.save()

                messages.success(request, "User updated successfully.")
                return redirect('user-and-roles')
            else:
                messages.error(request, 'Data Not Found. Kindly connect to admin department')
                return redirect('user-and-roles')
        else:
            messages.error(request, 'Invalid URL')
            return redirect('user-and-roles')
    else:
        return redirect('login')
    
def updateUserStatus(request):
    if request.user.is_authenticated:
        if request.method == "POST":
            user_id = request.POST.get('user_id', '').strip()
            
            if not user_id:
                messages.error(request,'Something Went Wrong. Kindly contact to administrator')
            
            user_data = Users.objects.filter(id=user_id).first()
            
            if user_data is not None:
                user_data.status = 2 if user_data.status == 1 else 1
                user_data.save()
                
                messages.success(request, "Status updated successfully.")
                return redirect('user-and-roles')
            else:       
                messages.error(request, 'Data Not Found. Kinldy connect to admin department')
                return redirect('user-and-roles')
        else:
            messages.error(request, 'Invalid URL')
            return redirect('user-and-roles')
    else:
        return redirect('login')

def browsePolicy(request):
    if not request.user.is_authenticated and request.user.is_active != 1:
        messages.error(request, "Please Login First")
        return redirect('login')
    if request.method == "POST" and request.FILES.get("image"):
        image = request.FILES["image"]
         # Validate ZIP file format
        if not image.name.lower().endswith(".pdf"):
            messages.error(request, "Invalid file format. Only pdf files are allowed.")
            return redirect("policy-mgt")
        
        if image.size > 2 * 1024 * 1024:  # 2MB = 1024*1024*2 bytes
            messages.error(request, "File too large. Maximum allowed size is 2 MB.")
            return redirect("policy-mgt")

        fs = FileSystemStorage()
        filename = fs.save(image.name, image)
        filepath = fs.path(filename)
        fileurl = fs.url(filename)
        extracted_text = extract_text_from_pdf(filepath)
        if "Error" in extracted_text:
            messages.error(request, extracted_text)
            return redirect('policy-mgt')
        
        member_id = request.user.id
       
        commision_rate = commisionRateByMemberId(member_id)
        insurer_rate = insurercommisionRateByMemberId(1)
        if commision_rate:
            od_percentage = commision_rate.od_percentage
            net_percentage = commision_rate.net_percentage
            tp_percentage = commision_rate.tp_percentage
        else:
            od_percentage = 0.0
            net_percentage = 0.0
            tp_percentage = 0.0
            
        if insurer_rate:
            insurer_od_percentage = insurer_rate.od_percentage
            insurer_net_percentage = insurer_rate.net_percentage
            insurer_tp_percentage = insurer_rate.tp_percentage
        else:
            insurer_od_percentage = 0.0
            insurer_net_percentage = 0.0
            insurer_tp_percentage = 0.0

        
        processed_text = process_text_with_chatgpt(extracted_text)
        if "error" in processed_text:
            PolicyDocument.objects.create(
                filename=image.name,
                extracted_text=processed_text,
                filepath=fileurl,
                rm_name=request.user.first_name,
                rm_id=request.user.id,
                od_percent=od_percentage,
                tp_percent=tp_percentage,
                net_percent=net_percentage,
                insurer_tp_commission   = insurer_tp_percentage,
                insurer_od_commission   = insurer_od_percentage,
                insurer_net_commission  = insurer_net_percentage,
                status=3,
            )
            
            messages.error(request, f"Failed to process policy")
            return redirect('policy-mgt')
        else:
            policy_number = processed_text.get("policy_number", None)
            if PolicyDocument.objects.filter(policy_number=policy_number).exists():
                messages.error(request, "Policy Number already exists.")
                return redirect('policy-mgt')
            
            vehicle_number = re.sub(r"[^a-zA-Z0-9]", "", processed_text.get("vehicle_number", ""))
            coverage_details = processed_text.get("coverage_details", [{}])
            od_premium = coverage_details.get('own_damage', {}).get('premium', 0)
            tp_premium = coverage_details.get('third_party', {}).get('premium', 0)
            PolicyDocument.objects.create(
                filename=image.name,
                extracted_text=processed_text,
                filepath=fileurl,
                rm_name=request.user.full_name,
                rm_id=request.user.id,
                insurance_provider=processed_text.get("insurance_company", ""),
                vehicle_number=vehicle_number,
                policy_number=policy_number,
                policy_issue_date=processed_text.get("issue_date", ""),
                policy_expiry_date=processed_text.get("expiry_date", ""),
                policy_start_date=processed_text.get('start_date', ""),
                policy_period=processed_text.get("policy_period", ""),
                holder_name=processed_text.get("insured_name", ""),
                policy_total_premium=processed_text.get("gross_premium", 0),
                policy_premium=processed_text.get("net_premium", 0),
                sum_insured=processed_text.get("sum_insured", 0),
                coverage_details=processed_text.get("coverage_details", ""),
                payment_status='Confirmed',
                policy_type=processed_text.get('additional_details', {}).get('policy_type', ""),
                vehicle_type=processed_text.get('vehicle_details', {}).get('vehicle_type', ""),
                vehicle_make=processed_text.get('vehicle_details', {}).get('make', ""),                      
                vehicle_model=processed_text.get('vehicle_details', {}).get('model', ""),                      
                vehicle_gross_weight=processed_text.get('vehicle_details', {}).get('vehicle_gross_weight', ""),                     
                vehicle_manuf_date=processed_text.get('vehicle_details', {}).get('registration_year', ""),                      
                gst=processed_text.get('gst_premium', 0),                      
                od_premium=od_premium,
                tp_premium=tp_premium,
                od_percent=od_percentage,
                tp_percent=tp_percentage,
                net_percent=net_percentage,
                insurer_tp_commission   = insurer_rate.tp_percentage,
                insurer_od_commission   = insurer_rate.od_percentage,
                insurer_net_commission  = insurer_rate.net_percentage,

                status=6,
            )
            messages.success(request, "PDF uploaded and processed successfully.")
            
        return redirect('policy-data')
    
    else:
        messages.error(request, "Please upload a PDF file.")

    return redirect('policy-mgt')

def parse_date(date_str):
    try:
        if date_str:
            return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
    except Exception:
        pass
    return None

def extract_text_from_pdf(pdf_path):
    try:
        doc = fitz.open(pdf_path)
        text = "\n".join(page.get_text("text") for page in doc)
        return text
    except Exception as e:
        return f"Error extracting text: {e}"

def process_text_with_chatgpt(text):

    prompt = f"""
    Convert the following insurance document text into a structured JSON format without any extra comments. Ensure that numerical values (like premiums and sum insured) are **only numbers** without extra text.  if godigit replace the amount of od and tp from one another 

    ```
    {text}
    ```

    The JSON should have this structure:
    
    {{
        "policy_number": "XXXXXX/XXXXX",   # complete policy number if insurance_company is godigit policy number is 'XXXXXX / XXXXX' in this format   e
        "vehicle_number": "XXXXXXXXXX",
        "insured_name": "XXXXXX",
        "issue_date": "YYYY-MM-DD H:i:s",     
        "start_date": "YYYY-MM-DD H:i:s",
        "expiry_date": "YYYY-MM-DD H:i:s",
        "gross_premium": XXXX,    
        "net_premium": XXXX,
        "gst_premium": XXXX,
        "sum_insured": XXXX,
        "policy_period": "XX Year(s)",
        "insurance_company": "XXXXX",
        "coverage_details": {{
            "own_damage": {{
                "premium": XXXX,
                "additional_premiums": XXXX,
                "addons": {{
                    "addons": [
                        {{ "name": "XXXX", "amount": XXXX }},
                        {{ "name": "XXXX", "amount": XXXX }}
                    ],
                    "discounts": [
                        {{ "name": "XXXX", "amount": XXXX }},
                        {{ "name": "XXXX", "amount": XXXX }}
                    ]
                }}
            }},
            "third_party": {{
                "premium": XXXX,
                "additional_premiums": XXXX,
                "addons": {{
                    "addons": [
                        {{ "name": "XXXX", "amount": XXXX }},
                        {{ "name": "XXXX", "amount": XXXX }}
                    ],
                    "discounts": [
                        {{ "name": "XXXX", "amount": XXXX }},
                        {{ "name": "XXXX", "amount": XXXX }}
                    ]
                }}
            }}
        }},
        "vehicle_details": {{
            "make": "XXXX",
            "model": "XXXX",
            "variant": "XXXX",
            "registration_year": YYYY,
            "manufacture_year": YYYY,
            "engine_number": "XXXXXXXXXXXX",
            "chassis_number": "XXXXXXXXXXXX",
            "fuel_type": "XXXX",     # diesel/petrol/cng/lpg/ev 
            "cubic_capacity": XXXX,  
            "seating_capacity": XXXX,  
            "vehicle_gross_weight": XXXX,   # in kg
            "vehicle_type": "XXXX XXXX",    # private / commercial
            "commercial_vehicle_detail": "XXXX XXXX"    
        }},
        "additional_details": {{
            "policy_type": "XXXX",        # motor stand alone policy/ motor third party liablity policy / motor package policy   only in these texts
            "ncb": XX,     # in percentage
            "addons": ["XXXX", "XXXX"], 
            "previous_insurer": "XXXX",
            "previous_policy_number": "XXXX"
        }},
        "contact_information": {{
            "address": "XXXXXX",
            "phone_number": "XXXXXXXXXX",
            "email": "XXXXXX",
            "pan_no": "XXXXX1111X",
            "aadhar_no": "XXXXXXXXXXXX"
        }}
    }}
    
    If some details are missing, leave them as blank.
    """

    api_url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }

    data = {
        "model": "gpt-4o",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0
    }

    try:
        log_entry = ChatGPTLog.objects.create(
            prompt=prompt,
            created_at=now()
        )
    except:
        logger.error(f"Error In ChatGPT logentry")
        
    try:
        response = requests.post(api_url, json=data, headers=headers)

        if hasattr(response, "status_code"):
            log_entry.status_code = response.status_code
            
        if hasattr(response, "status_code") and response.status_code == 200:

            result = response.json()
            raw_output = result["choices"][0]["message"]["content"].strip()
            
            try:
                clean_json = re.sub(r"```json\n|\n```|```", "", raw_output).strip()
                
                parsed_json = json.loads(clean_json)
                log_entry.response = json.dumps(parsed_json, indent=4)
                log_entry.is_successful = True
                log_entry.save()
                return parsed_json
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error {str(e)}")
                log_entry.response = raw_output
                log_entry.error_message = f"JSON decode error: {str(e)}"
                log_entry.save()
                
                return json.dumps({
                    "error": "JSON decode error",
                    "raw_output": raw_output,
                    "details": str(e)
                }, indent=4)
        else:
            log_entry.error_message = response.text
            log_entry.save()
            return json.dumps({"error": f"API Error: {response.status_code}", "details": response.text}, indent=4)
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed ,details: {str(e)}")
        
        log_entry.error_message = str(e)
        log_entry.save()
        
        return json.dumps({"error": "Request failed", "details": str(e)}, indent=4)

def policyData(request):
    if not request.user.is_authenticated:
        return redirect('login')
    user_id = request.user.id
    role_id = Users.objects.filter(id=user_id).values_list('role_id', flat=True).first()

    filters_q = Q(status=6) & Q(policy_number__isnull=False) & ~Q(policy_number='')
    if role_id != 1 and request.user.department_id != "5" and request.user.department_id != "3":
        filters_q &= Q(rm_id=user_id)
        
    base_qs = PolicyDocument.objects.filter(filters_q).order_by('-id').prefetch_related(
        'policy_agent_info', 'policy_franchise_info', 'policy_insurer_info'
    )
    
    def get_nested(data, path, default=''):
        for key in path:
            data = data.get(key) if isinstance(data, dict) else default
        return str(data).lower()



    filters = {
        'policy_number':      request.GET.get('policy_number', '').strip().lower(),
        'vehicle_number':     request.GET.get('vehicle_number', '').strip().lower(),
        'engine_number':      request.GET.get('engine_number', '').strip().lower(),
        'chassis_number':     request.GET.get('chassis_number', '').strip().lower(),
        'vehicle_type':       request.GET.get('vehicle_type', '').strip().lower(),
        'policy_holder_name':      request.GET.get('policy_holder_name', '').strip().lower(),      # maps to "Customer Name"
        'mobile_number':      request.GET.get('mobile_number', '').strip().lower(),      # maps to "Mobile Number"
        'insurance_provider': request.GET.get('insurance_provider', '').strip().lower(), # maps to "Insurance Provider"
    }

    filtered = []
    for obj in base_qs:
        raw = obj.extracted_text
        data = {}
        
        if isinstance(raw, str):
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue
        elif isinstance(raw, dict):
            data = raw
    
        if not data:
            continue

        if filters['policy_number'] and filters['policy_number'] not in data.get('policy_number', '').lower():
            continue
        if filters['vehicle_number'] and filters['vehicle_number'] not in data.get('vehicle_number', '').lower():
            continue
        if filters['engine_number'] and filters['engine_number'] not in get_nested(data, ['vehicle_details', 'engine_number']).lower():
            continue
        if filters['chassis_number'] and filters['chassis_number'] not in get_nested(data, ['vehicle_details', 'chassis_number']).lower():
            continue
        if filters['vehicle_type'] and filters['vehicle_type'] not in get_nested(data, ['vehicle_details', 'vehicle_type']).lower():
            continue
        if filters['policy_holder_name'] and filters['policy_holder_name'] not in data.get('insured_name', '').lower():
            continue
        if filters['mobile_number'] and filters['mobile_number'] not in data.get('contact_information', {}).get('phone_number', '').lower():
            continue
        if filters['insurance_provider'] and filters['insurance_provider'] not in data.get('insurance_company', '').lower():
            continue   

        obj.json_data = data    # attach parsed dict for the template
        filtered.append(obj)

    if role_id != 1 and request.user.department_id != "5":
        policy_count = PolicyDocument.objects.filter(status=6, rm_id=user_id).count()
    else:
        policy_count = PolicyDocument.objects.filter(status=6).count()

    # Pagination
    per_page = request.GET.get('per_page', 10)
    try:
        per_page = int(per_page)
    except ValueError:
        per_page = 10

    paginator = Paginator(filtered, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'policy/policy-data.html', {
        "page_obj": page_obj,
        "policy_count": policy_count,
        "per_page": per_page,
        'filters': {k: request.GET.get(k,'') for k in filters}
    })

def editPolicy(request, id):
    if request.user.is_authenticated:
        policy_data = PolicyDocument.objects.filter(id=id).first()
        policy_number = policy_data.policy_number
        policy = PolicyInfo.objects.filter(policy_number=policy_number).first()
        pdf_path = get_pdf_path(request, policy_data.filepath)
        branches = Branch.objects.filter(status='Active').order_by('-created_at')
        referrals = Referral.objects.all()

        extracted_data = {}
        if policy_data and policy_data.extracted_text:
            if isinstance(policy_data.extracted_text, str):
                try:
                    extracted_data = json.loads(policy_data.extracted_text)
                except json.JSONDecodeError:
                    extracted_data = {}
            elif isinstance(policy_data.extracted_text, dict):
                extracted_data = policy_data.extracted_text  # already a dict
        return render(request, 'policy/edit-policy.html', {
            'policy_data': policy_data,
            'policy': policy,
            'referrals': referrals,
            'branches': branches,
            'pdf_path': pdf_path,
            'extracted_data': extracted_data,
            'file_path': policy_data.filepath,
        })
    else:
        return redirect('login')
   
def get_pdf_path(request, filepath):
    """
    Returns the absolute URI to the PDF file if it exists, otherwise an empty string.
    """
    if not filepath:
        return ""

    filepath_str = str(filepath).replace('\\', '/')
    rel_path = ""
    
    if 'media/' in filepath_str:
        rel_path = filepath_str.split('media/')[-1]
        absolute_file_path = os.path.join(settings.MEDIA_ROOT, rel_path)

        if not os.path.exists(absolute_file_path):
            # Try fallback inside empPortal/media
            fallback_path = os.path.join(settings.BASE_DIR, 'empPortal', 'media', rel_path)
            if os.path.exists(fallback_path):
                absolute_file_path = fallback_path
            else:
                rel_path = ""  # File not found in either location

        if rel_path:
            media_url_path = urljoin(settings.MEDIA_URL, rel_path.replace('\\', '/'))
            return request.build_absolute_uri(media_url_path)

    return ""

def parse_date(date_str):
    """Convert DD-MM-YYYY to YYYY-MM-DD format."""
    try:
        return datetime.strptime(date_str, "%d-%m-%Y").date() if date_str else None
    except ValueError:
        return None  # Handle invalid date formats gracefully

def updatePolicy(request):
    if not request.user.is_authenticated:
        return redirect('login')

    if request.method != "POST":
        messages.error(request, 'Invalid URL')
        return redirect('policy-data')
    
    policy_id = request.POST.get('policy_id', '').strip()
    insurer_name = request.POST.get('insurer_name', '').strip()
    policy_number = request.POST.get('policy_number', '').strip()
    vehicle_reg_no = request.POST.get('vehicle_reg_no', '').strip()
    policy_holder_name = request.POST.get('policy_holder_name', '').strip()
    policy_issue_date = parse_date(request.POST.get('policy_issue_date', '').strip())
    policy_start_date = parse_date(request.POST.get('policy_start_date', '').strip())
    policy_expiry_date = parse_date(request.POST.get('policy_expiry_date', '').strip())
    policy_premium = request.POST.get('policy_premium', '').strip()
    policy_total_premium = request.POST.get('policy_total_premium', '').strip()
    policy_gst = request.POST.get('policy_gst', '').strip()
    policy_period = request.POST.get('policy_period', '').strip()
    rm_name = request.POST.get('rm_name', '').strip()
    vehicle_type = request.POST.get('vehicle_type', '').strip()
    vehicle_make = request.POST.get('vehicle_make', '').strip()
    vehicle_model = request.POST.get('vehicle_model', '').strip()
    gross_weight = request.POST.get('gross_weight', '').strip()
    mgf_year = request.POST.get('mgf_year', '').strip()
    sum_insured = request.POST.get('sum_insured', '').strip()
    od_premium = request.POST.get('od_premium', '').strip()
    tp_premium = request.POST.get('tp_premium', '').strip()


    if not policy_id:
        messages.error(request, 'Something Went Wrong. Kindly contact the administrator.')
        return redirect(request.META.get('HTTP_REFERER', '/'))

    # Ensure policy number is unique
    if PolicyDocument.objects.filter(policy_number=policy_number).exclude(id=policy_id).exists():
        messages.error(request, "Policy Number already exists.")
        return redirect(request.META.get('HTTP_REFERER', '/'))

    policy_data = PolicyDocument.objects.filter(id=policy_id).first()

    if policy_data:
        policy_data.insurance_provider = insurer_name
        policy_data.policy_number = policy_number
        policy_data.vehicle_number = vehicle_reg_no
        policy_data.holder_name = policy_holder_name
        policy_data.policy_issue_date = policy_issue_date
        policy_data.policy_start_date = policy_start_date
        policy_data.policy_expiry_date = policy_expiry_date
        policy_data.policy_premium = policy_premium
        policy_data.policy_total_premium = policy_total_premium
        policy_data.gst = policy_gst
        policy_data.policy_period = policy_period
        policy_data.vehicle_type = vehicle_type
        policy_data.vehicle_make = vehicle_make
        policy_data.vehicle_model = vehicle_model
        policy_data.vehicle_gross_weight = gross_weight
        policy_data.vehicle_manuf_date = mgf_year
        policy_data.sum_insured = sum_insured
        policy_data.od_premium = od_premium
        policy_data.tp_premium = tp_premium
        policy_data.rm_name = rm_name
        policy_data.save()

        messages.success(request, 'Policy updated successfully.')
        return redirect('policy-data')

    messages.error(request, 'No Data Found')
    return redirect(request.META.get('HTTP_REFERER', '/'))

def changePassword(request):
    return render(request, 'change-password.html')

def updatePassword(request):
    if request.method == "POST":
        user = request.user
        current_password = request.POST.get("current_password", "").strip()
        new_password = request.POST.get("new_password", "").strip()
        confirm_password = request.POST.get("confirm_password", "").strip()

        if not current_password or not new_password or not confirm_password:
            messages.error(request, "All fields are required.")
            return redirect("change-password")

        if not user.check_password(current_password):
            messages.error(request, "Current password is incorrect.")
            return redirect("change-password")

        if new_password != confirm_password:
            messages.error(request, "New password and confirm password do not match.")
            return redirect("change-password")

        user.set_password(new_password)
        user.save()

        update_session_auth_hash(request, user)

        messages.success(request, "Your password has been updated successfully.")
        return redirect("dashboard") 

    return redirect("change-password")

def userLogout(request):
    if request.method == "POST":
        logout(request)
        messages.success(request, "You have been logged out successfully.")
        return redirect("login")
    else:
        return redirect("login")
        
def failedPolicyUploadView(request, id):
    if not request.user.is_authenticated:
        return redirect('login')

    # Correct the filter logic
    unprocessable_files = UnprocessedPolicyFiles.objects.filter(bulk_log_id=id, status=1)

    return render(request, 'policy/unprocessable-files.html', {'files': unprocessable_files})
  

def reprocessBulkPolicies(request):
    if not request.user.is_authenticated and request.user.is_active == 1:
        return redirect('login')
    if request.method == "POST":
        unprocessFiles = request.POST.get('reprocess_bulk_policies', '')
        
        if not unprocessFiles:
            messages.error(request,'Select Atleast One Policy')
            return redirect(request.META.get('HTTP_REFERER', '/'))
            
        unprocessFilesList = unprocessFiles.split(",") if unprocessFiles else []
        
        for file_id in unprocessFilesList:
            try:
                file_data = UnprocessedPolicyFiles.objects.get(id=file_id)

                individual_file_id = file_data.policy_document 
                bulk_log_id = file_data.bulk_log_id
                
                stored_path = file_data.file_path
                
                if stored_path.startswith("/media/"):
                    stored_path = stored_path.replace("/media/", "", 1)

                file_path = os.path.normpath(os.path.join(settings.MEDIA_ROOT, stored_path))

                extracted_text = extract_text_from_pdf(file_path)

                if "Error" in extracted_text:
                    continue
                
                processed_text = process_text_with_chatgpt(extracted_text)
                if "error" in processed_text:
                    policy_doc = PolicyDocument.objects.filter(id=individual_file_id).first()
                    policy_doc.extracted_text = processed_text
                    policy_doc.save()
                    
                    unprocess_policy = UnprocessedPolicyFiles.objects.filter(id=file_id).first()
                    unprocess_policy.error_message=processed_text
                    unprocess_policy.save()
                    
                else:
                    policy_number = processed_text.get("policy_number", None)
                    if PolicyDocument.objects.filter(policy_number=policy_number).exists():
                        continue
                    
                    vehicle_number = re.sub(r"[^a-zA-Z0-9]", "", processed_text.get("vehicle_number", ""))
                    coverage_details = processed_text.get("coverage_details", [{}])
                    first_coverage = coverage_details if coverage_details else {}

                    od_premium = first_coverage.get('own_damage', {}).get('premium', 0)
                    tp_premium = first_coverage.get('third_party', {}).get('premium', 0)
                    
                    policy_doc = PolicyDocument.objects.filter(id=individual_file_id).first()
                    
                    policy_doc.extracted_text = processed_text
                    policy_doc.insurance_provider = processed_text.get("insurance_company", "")
                    policy_doc.vehicle_number = vehicle_number
                    policy_doc.policy_number=policy_number
                    policy_doc.policy_issue_date=processed_text.get("issue_date", None)
                    policy_doc.policy_expiry_date=processed_text.get("expiry_date", None)
                    policy_doc.policy_period=processed_text.get("policy_period", "")
                    policy_doc.holder_name=processed_text.get("insured_name", "")
                    policy_doc.policy_total_premium=processed_text.get("gross_premium", 0)
                    policy_doc.policy_premium=processed_text.get("net_premium", 0)
                    policy_doc.sum_insured=processed_text.get("sum_insured", 0)
                    policy_doc.coverage_details=processed_text.get("coverage_details", "")
                    policy_doc.policy_start_date=processed_text.get('start_date', None)
                    policy_doc.payment_status='Confirmed'
                    policy_doc.policy_type=processed_text.get('additional_details', {}).get('policy_type', "")
                    policy_doc.vehicle_type=processed_text.get('vehicle_details', {}).get('vehicle_type', "")
                    policy_doc.vehicle_make=processed_text.get('vehicle_details', {}).get('make', "")               
                    policy_doc.vehicle_model=processed_text.get('vehicle_details', {}).get('model', "")
                    policy_doc.vehicle_gross_weight=processed_text.get('vehicle_details', {}).get('vehicle_gross_weight', "") 
                    policy_doc.vehicle_manuf_date=processed_text.get('vehicle_details', {}).get('registration_year', "")                  
                    policy_doc.gst=processed_text.get('gst_premium', 0)
                    policy_doc.od_premium=od_premium
                    policy_doc.tp_premium=tp_premium
                    policy_doc.status=6
                    policy_doc.save()
                    
                    bulk_log = BulkPolicyLog.objects.filter(id=bulk_log_id).first()
                    bulk_log.count_error_process_pdf_files -= 1
                    bulk_log.count_uploaded_files += 1
                    bulk_log.save()
                    
                    unprocess_policy = UnprocessedPolicyFiles.objects.filter(id=file_id).first()
                    unprocess_policy.error_message=''
                    unprocess_policy.status="Reprocessed"
                    unprocess_policy.save()
                    
            except UnprocessedPolicyFiles.DoesNotExist:
                print(f"File with ID {file_id} not found")

        return redirect('bulk-upload-logs')
    else:
        messages.error(request, 'Invalid URL')
        return redirect(request.META.get('HTTP_REFERER', '/'))

def continueBulkPolicies(request):
    if not request.user.is_authenticated or request.user.is_active != 1:
        return redirect('login')
    if request.method == "POST":
        log_id = request.POST.get('log_id', None)
        if log_id == None:
            return redirect('bulk-upload-logs')
        
        reprocessFiles = request.POST.get('continue_bulk_policies', '')
        
        if not reprocessFiles:
            messages.error(request,'Select Atleast One Policy')
            return redirect(request.META.get('HTTP_REFERER', '/'))
            
        reprocessFilesList = reprocessFiles.split(",") if reprocessFiles else []
        
        for file_id in reprocessFilesList:
            async_task('empPortal.tasks.reprocessFiles', file_id)

        return redirect('bulk-policies',log_id)
    else:
        messages.error(request, 'Invalid URL')
        return redirect(request.META.get('HTTP_REFERER', '/'))

def getUserNameByUserId(user_id):
    try:
        return Users.objects.get(id=user_id).full_name
    except Users.DoesNotExist:
        return None

def commisionRateByMemberId(member_id):
    commission_data = Commission.objects.filter(member_id=member_id).first()
    return commission_data

def insurercommisionRateByMemberId(member_id):
    commission_data = Commission.objects.filter(member_id=member_id).first()
    return commission_data
