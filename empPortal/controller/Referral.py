import logging
import re
from django.shortcuts import render,redirect, get_object_or_404
import openpyxl
from empPortal.model import Referral
from ..models import Franchises, Department,RefUploadedExcel, Branch, Users
from django.db.models import OuterRef, Subquery
from django.contrib import messages
from datetime import date, datetime
from ..models import BulkPolicyLog,ExtractedFile, BqpMaster, SingleUploadFile
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
from django_q.tasks import async_task
# from empPortal.tasks.referral_task import ref_BulkUpload
from django.contrib.auth.decorators import login_required
from empPortal.model import Employees
from django.db.models import Exists, OuterRef




logger = logging.getLogger(__name__)

def dictfetchall(cursor):
    "Returns all rows from a cursor as a dict"
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

def index(request):
    if not request.user.is_authenticated:
        return redirect('login')

    per_page = request.GET.get('per_page', 10)
    search_field = request.GET.get('search_field', '')
    search_query = request.GET.get('search_query', '')
    sort_by = request.GET.get('sort_by', '')

    try:
        per_page = int(per_page)
    except ValueError:
        per_page = 10

    # department_id = request.user.department_id
   
    role_id = request.user.role_id
    user_id = request.user.id

    referrals = Referral.objects.filter(referral_is_delete=False)  # Default empty queryset

    if role_id == 2:  # Management
        referrals = referrals

    elif role_id == 3:  # Branch Manager
        managers = Users.objects.filter(role_id=5, senior_id=user_id)
        team_leaders = Users.objects.filter(role_id=6, senior_id__in=managers.values_list('id', flat=True))
        relationship_managers = Users.objects.filter(role_id=7, senior_id__in=team_leaders.values_list('id', flat=True))

        user_ids = list(managers.values_list('id', flat=True)) + \
                   list(team_leaders.values_list('id', flat=True)) + \
                   list(relationship_managers.values_list('id', flat=True))
        referrals = referrals.filter(supervisor__in=user_ids)

    elif role_id == 4:  # Agent
        referrals = referrals.filter(supervisor=user_id)  # Agent can only see themselves

    elif role_id == 5:  # Manager
        team_leaders = Users.objects.filter(role_id=6, senior_id=user_id)
        relationship_managers = Users.objects.filter(role_id=7, senior_id__in=team_leaders.values_list('id', flat=True))

        user_ids = list(team_leaders.values_list('id', flat=True)) + \
                   list(relationship_managers.values_list('id', flat=True)) 
        referrals = referrals.filter(supervisor__in=user_ids)

    elif role_id == 6:  # Team Leader
        relationship_managers = Users.objects.filter(role_id=7, senior_id=user_id)
        user_ids = list(relationship_managers.values_list('id', flat=True))
        referrals = referrals.filter(supervisor__in=user_ids)

    elif role_id == 7:  # Relationship Manager
        referrals = referrals.filter(supervisor=user_id)

    else:
        referrals = referrals

    # Apply Filter on fields  ##
    if 'name' in request.GET and request.GET['name']:
        referrals =referrals.filter(name__icontains=request.GET['name'])
    if 'referral_code' in request.GET and request.GET['referral_code']:
        referrals =referrals.filter(referral_code__icontains=request.GET['referral_code'])
    if 'email' in request.GET and request.GET['email']:
        referrals = referrals.filter(email__icontains=request.GET['email']) 
    if 'mobile' in request.GET and request.GET['mobile']:
        referrals = referrals.filter(mobile__icontains=request.GET['mobile'])         


    # Sorting
    if sort_by == 'name-a_z':
        referrals = referrals.order_by('name')
    elif sort_by == 'name-z_a':
        referrals = referrals.order_by('-name')
    elif sort_by == 'recently_created':
        referrals = referrals.order_by('-created_at')
    elif sort_by == 'recently_updated':
        referrals = referrals.order_by('-updated_at')
    elif sort_by == 'active_first':
        referrals = referrals.order_by('-active', '-created_at')
    elif sort_by == 'inactive_first':
        referrals = referrals.order_by('active', '-created_at')
    else:
        referrals = referrals.order_by('-created_at')  # default

    total_count = referrals.count()

    # Pagination
    paginator = Paginator(referrals, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'referral/index.html', {
        'page_obj': page_obj,
        'total_count': total_count,
        'search_field': search_field,
        'search_query': search_query,
        'per_page': per_page,
        'sort_by': sort_by,
        'referrals':referrals,
    })
    
def create_or_edit(request, referral_id=None):
    if not request.user.is_authenticated:
        return redirect('login')

    referral = None
    is_editing = False

    if referral_id:
        referral = get_object_or_404(Referral, id=referral_id)
        is_editing = True

    branchs = Branch.objects.filter(status='Active')
    # sales_managers = Users.objects.filter(department_id=1,role_id=5,is_active=1)
        
    sales_managers = Users.objects.annotate(
        employee_exists=Exists(
            Employees.objects.filter(user_id=OuterRef('id'))
        )
    ).filter(
        department_id='1',  # Use string if department_id is varchar in DB
        role_id=5,
        employee_exists=True,
        is_active=1
    )

    bqps = BqpMaster.objects.all().order_by('bqp_fname')

    relationship_managers = Users.objects.filter(department_id=1,is_active=1,role_id=7)  #only sales dept relationship manager 
    # franchises = Franchises.objects.filter(status="Active")
    if request.method == "GET":
        return render(request, 'referral/create.html', {
            'referral': referral,
            'is_editing': is_editing,
            'bqps': bqps,
            'branchs': branchs,
            'sales_managers':sales_managers,
            # 'franchises':franchises,
            'relationship_managers':relationship_managers
        })

    elif request.method == "POST":
        name = request.POST.get("name", "").strip()
        mobile = request.POST.get("mobile", "").strip()
        email = request.POST.get("email", "").strip()
        address = request.POST.get("address", "").strip()

        ## add field ## ---parth
        dob = request.POST.get("dob", "").strip()
        date_of_anniversary = request.POST.get("date_of_anniversary", "").strip()
        pan_card_number = request.POST.get("pan_card_number", "").strip()
        aadhar = request.POST.get("aadhar", "").strip()

        user_role = request.POST.get("user_role", "").strip()
        bqp_id = request.POST.get("bqp_id", "").strip()
        branch = request.POST.get("branch", "").strip()
        sales = request.POST.get("sales", "").strip()
        supervisor = request.POST.get("supervisor", "").strip()
        franchise = request.POST.get("franchise", "").strip()
        pincode = request.POST.get("pincode", "").strip()
        city = request.POST.get("city", "").strip()
        state = request.POST.get("state", "").strip()



        referral_code = (
            referral.referral_code if referral
            else generate_referral_code()
        )

        # Pre-fill values in case of error
        form_data = {
            "name": name,
            "mobile": mobile,
            "email": email,
            "address": address,
            "dob": dob,
            "date_of_anniversary": date_of_anniversary,
            "pan_card_number": pan_card_number,
            "aadhar_no": aadhar,
            "user_role": user_role,
            "bqp_id": bqp_id,
            "branch": branch,
            "sales": sales,
            "supervisor": supervisor,
            "franchise": franchise,
            "pincode": pincode,
            "city": city,
            "state": state,
            "referral_code": referral_code,
        }

        # === Validation ===
        if referral:
            if not name:
                messages.error(request,"Name is required.")
            elif not re.match(r'^[a-zA-Z\s]+$',name):
                 messages.error(request,"Invalid name. Only letters and spaces are allowed.")
                 return render(request,'referral/create.html', {
                    'referral': form_data,
                    'is_editing': True,
                })
            
            if dob:
                try:
                    dob_date = datetime.strptime(dob,'%Y-%m-%d').date()
                    today = date.today()

                    if dob_date >= today:
                        messages.error(request,"Date of birth must be in the past2")
                        return render(request,'referral/create.html',{
                        'referral': form_data,
                        'is_editing': True,
                    })
                except ValueError:
                    messages.error(request,"Invalid Date of Birth Format.")
                    return render(request,'referral/create.html',{
                        'referral': form_data,
                        'is_editing': True,
                    })


            # Mobile Number -- Required,Format and Uniqueness## ----check
            if not mobile:
              messages.error(request, "Mobile Number is required.")
              return render(request, 'referral/create.html', {'referral': form_data, 'is_editing': True})
            if Referral.objects.exclude(id=referral.id).filter(mobile=mobile).exists():
               messages.error(request, "Mobile number already exists.")
               return render(request, 'referral/create.html', {'referral': form_data, 'is_editing': True})

            # For update, exclude current record from uniqueness checks
            # if Referral.objects.exclude(id=referral.id).filter(email=email).exists():
            #     messages.error(request, "Email already exists.")
            #     return render(request, 'referral/create.html', {
            #         'referral': form_data,
            #         'is_editing': True,
            #     })

            # PAN Card - 1--> Required & 2--> Format
            if not pan_card_number:
                messages.error(request,"Pan card number is required.")
            elif not re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]$',pan_card_number):
                messages.error(request,"Invalid PAN card format. Example:'ABCDE1234F'.")
                return render(request, 'referral/create.html', {
                    'referral': form_data,
                    'is_editing': True,
                })
            
            # Aadhar Number - 1-->Required & 2-->Format
            if not aadhar:
                 messages.error(request, "Aadhar number is required.")
            elif not re.match(r'^\d{12}$', aadhar):
                 messages.error(request, "Invalid Aadhar number. It must be exactly 12 digits.")
                 return render(request, 'referral/create.html', {
                    'referral': form_data,
                    'is_editing': True,
                }) 


            # if mobile and Referral.objects.exclude(id=referral.id).filter(mobile=mobile).exists():
            #     messages.error(request, "Mobile number already exists.")
            #     return render(request, 'referral/create.html', {
            #         'referral': form_data,
            #         'is_editing': True,
            #     })

            # Pincode - 1---> Required & 2---> Format
            if not pincode:
                messages.error(request, "Pincode is required.")
            elif not re.match(r'^\d{6}$', pincode):
                messages.error(request, "Invalid pincode. It must be exactly 6 digits.")
                return render(request, 'referral/create.html', {
                    'referral': form_data,
                    'is_editing': True,
                })
            
            # if not email or "@" not in email:
            #       messages.error(request,"Invalid email address.")
            
            # elif Referral.objects.exclude(id=referral.id).filter(email=email).exists():
            #       messages.error(request, "Email is already registered.")
            #       return render(request, 'referral/create.html', {
            #         'referral': form_data,
            #         'is_editing': True,
            #     })


            # Email validation
            if not email:
               messages.error(request, "Email is required.")
               return render(request, 'referral/create.html', {'referral': form_data, 'is_editing': True})
            if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
               messages.error(request, "Invalid email address.")
               return render(request, 'referral/create.html', {'referral': form_data, 'is_editing': True})
            if Referral.objects.exclude(id=referral.id).filter(email=email).exists():
               messages.error(request, "Email already exists.")
               return render(request, 'referral/create.html', {'referral': form_data, 'is_editing': True})

        

            # Save updates
            referral.name = name
            referral.email = email
            referral.mobile = mobile
            referral.address = address

            referral.dob = dob or None
            referral.date_of_anniversary = date_of_anniversary or None
            referral.pan_card_number = pan_card_number
            referral.aadhar_no = aadhar

            referral.user_role = user_role
            referral.bqp_id = bqp_id
            referral.branch = branch
            referral.sales = sales
            referral.supervisor = supervisor
            referral.franchise = franchise
            referral.pincode = pincode
            referral.city = city
            referral.state = state


            referral.updated_at = now()
            referral.save()

            messages.success(request, f"Referral updated successfully! ID: {referral.id}")
            return redirect(reverse("referral-management"))

        else:

            if not name:
                messages.error(request,"Name is required.")
            elif not re.match(r'^[a-zA-Z\s]+$',name):
                 messages.error(request,"Invalid name. Only letters and spaces are allowed.")
                 return render(request,'referral/create.html', {
                    'referral': form_data,
                    'is_editing': False,
                })
            
             # Mobile Number -- Required,Format and Uniqueness## ----check
            if not mobile:
               messages.error(request, "Mobile Number is required.")
               return render(request, 'referral/create.html', {'referral': form_data, 'is_editing': False})
            if Referral.objects.filter(mobile=mobile).exists():
               messages.error(request, "Mobile number already exists.")
               return render(request, 'referral/create.html', {'referral': form_data, 'is_editing': False})

            
            # PAN Card - 1--> Required & 2--> Format
            if not pan_card_number:
                messages.error(request,"Pan card number is required.")
            elif not re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]$',pan_card_number):
                messages.error(request,"Invalid PAN card format. Example:'ABCDE1234F'.")
                return render(request, 'referral/create.html', {
                    'referral': form_data,
                    'is_editing': False,
                })
            
            if dob:
                try:
                   dob_date = datetime.strptime(dob,'%Y-%m-%d').date()
                   today = date.today()

                   if dob_date >= today:
                    messages.error(request,"Date of birth must be in the past2")
                    return render(request,'referral/create.html',{
                    'referral': form_data,
                    'is_editing': False,
                     })
                except ValueError:
                       messages.error(request,"Invalid Date of Birth Format.")
                       return render(request,'referral/create.html',{
                       'referral': form_data,
                       'is_editing': False,
                       })
            
            # Aadhar Number - 1-->Required & 2-->Format
            if not aadhar:
                 messages.error(request, "Aadhar number is required.")
            elif not re.match(r'^\d{12}$', aadhar):
                 messages.error(request, "Invalid Aadhar number. It must be exactly 12 digits.")
                 return render(request, 'referral/create.html', {
                    'referral': form_data,
                    'is_editing': False,
                }) 

             # Pincode - 1---> Required & 2---> Format
            if not pincode:
                messages.error(request, "Pincode is required.")
            elif not re.match(r'^\d{6}$', pincode):
                messages.error(request, "Invalid pincode. It must be exactly 6 digits.")
                return render(request, 'referral/create.html', {
                    'referral': form_data,
                    'is_editing': False,
                }) 
            

            if not email:
               messages.error(request, "Email is required.")
               return render(request, 'referral/create.html', {'referral': form_data, 'is_editing': False})
            if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
               messages.error(request, "Invalid email address.")
               return render(request, 'referral/create.html', {'referral': form_data, 'is_editing': False})
            if Referral.objects.filter(email=email).exists():
               messages.error(request, "Email already exists.")
               return render(request, 'referral/create.html', {'referral': form_data, 'is_editing': False})
 
            
            # if not email or "@" not in email:
            #       messages.error(request,"Invalid email address.")
            # elif Referral.objects.exclude(id=referral.id).filter(email=email).exists():
            #       messages.error(request, "Email is already registered.")
            #       return render(request, 'referral/create.html', {
            #         'referral': form_data,
            #         'is_editing': True,
            #     })       
            

            # # For create, check full uniqueness
            # if Referral.objects.filter(email=email).exists():
            #     messages.error(request, "Email already exists.")
            #     return render(request, 'referral/create.html', {
            #         'referral': form_data,
            #         'is_editing': False,
            #     })

            # if mobile and Referral.objects.filter(mobile=mobile).exists():
            #     messages.error(request, "Mobile number already exists.")
            #     return render(request, 'referral/create.html', {
            #         'referral': form_data,
            #         'is_editing': False,
            #     })

            new_referral = Referral.objects.create(
                name=name,
                email=email,
                mobile=mobile,
                address=address,
                referral_code=referral_code,

                dob=dob or None,
                date_of_anniversary=date_of_anniversary or None,
                pan_card_number=pan_card_number,
                aadhar_no=aadhar,

                user_role=user_role,
                bqp_id=bqp_id,
                branch=branch,
                sales=sales,
                supervisor=supervisor,
                franchise=franchise,
                pincode=pincode,
                city=city,
                state=state,


                created_at=now(),
                updated_at=now(),
            )

            messages.success(request, f"Referral created successfully! ID: {new_referral.id}")
            return redirect(reverse("referral-management"))
            # return redirect(reverse("ref_bank_details",kwargs={'referral_id': new_referral.id}))
        


def generate_referral_code():
    last_referral = Referral.objects.order_by('-id').first()
    next_id = 1 if not last_referral else last_referral.id + 1
    return f"REF{str(next_id).zfill(4)}"  # e.g., REF0001, REF0023

def toggle_referral_status(request, referral_id):
    """Toggle referral active status (Activate/Deactivate)"""
    if request.method == "POST":
        referral = get_object_or_404(Referral, id=referral_id)

        # Toggle boolean status
        referral.active = not referral.active
        referral.save()

        status_text = "Active" if referral.active else "Inactive"

        return JsonResponse({
            "success": True,
            "message": f"Referral status updated to {status_text}",
            "status": status_text,
            "referral_id": referral.id
        })

    return JsonResponse({"success": False, "message": "Invalid request method!"}, status=400)


# def ref_bulk_upload(request):
#     if request.method == "POST":
#         excel_file = request.FILES.get('excel_file')
#         ## Excel Fles Validity Checks ##
#         if not excel_file:
#             messages.error(request, "No file uploaded.")
#             return redirect('referral-bulk-upload')
#         elif not excel_file.name.lower().endswith(".xlsx"):
#              messages.error(request,"Invalid file format. Only .xlsx and .xls files are allowed.")
#              return redirect('referral-bulk-upload')
#         elif excel_file.size > 5 * 1024 * 1024:
#             messages.error(request,"File too large. Maximum allowed size is 5 MB.")
#             return redirect('referral-bulk-upload')


#         try:
#             df = pd.read_excel(excel_file)

#             for index, row in df.iterrows():
#                 name = str(row.get('Name', '')).strip()
#                 user_role = str(row.get('User Role', '')).strip()
#                 branch = str(row.get('Branch', '')).strip()
#                 sales = str(row.get('Sales Manger', '')).strip()
#                 supervisor = str(row.get('Supervisor', '')).strip()
#                 franchise = str(row.get('Franchise', '')).strip()
#                 mobile = str(row.get('Mobile Number', '')).strip()
#                 email = str(row.get('Email', '')).strip()
#                 dob = row.get('Date of Birth')
#                 date_of_anniversary = row.get('Anniversary Date')
#                 address = str(row.get('Address', '')).strip()
#                 pincode = str(row.get('Pincode', '')).strip()
#                 city = str(row.get('City', '')).strip()
#                 state = str(row.get('State', '')).strip()
#                 pan_card_number = str(row.get('Pan Number', '')).upper().strip() 
#                 aadhar_no = str(row.get('Aadhar Number', '')).strip()


#                 ## Validation In Excel Sheets ## 
#                 if not name or not mobile or not email or not pan_card_number or not aadhar_no:
#                     continue
#                 if Referral.objects.filter(
#                      Q(mobile=mobile) | Q(email=email) | Q(pan_card_number=pan_card_number) | Q(aadhar_no=aadhar_no)
#                     ).exists():
#                      logger.error(f"Row{index + 2} skipped: Duplicate mobile number, email, Pan card, Aadhar number")
#                      continue
                
#                 ## Validation On field Excel Sheets ##
#                 if not re.match(r"^[6-9][0-9]{9}$",str(mobile)):
#                      logger.error(f"Row{index + 2} skipped: Invalid mobile number format")
#                      continue
                
#                 if not re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]$',str(pan_card_number)):
#                     logger.error(f"Row{index + 2} skipped: Invalid Pan number format")
#                     continue

#                 if not re.match(r'^[2-9][0-9]{11}$', str(aadhar_no)):
#                     logger.error(f"Row{index + 2} skipped:Invalid Aadhar number format. I will have 12 digit, Not start with 0 and 1")
#                     continue

#                 # if Referral.objects.filter(email=email).exists():
#                 #     continue
#                 # if Referral.objects.filter(pan_card_number=pan_card_number).exists():
#                 #     continue
#                 # if Referral.objects.filter(aadhar_no=aadhar_no).exists():
#                 #     continue


#                 Referral.objects.create(
#                     name=name,
#                     user_role=user_role,
#                     branch=branch,
#                     sales=sales,
#                     supervisor=supervisor,
#                     franchise=franchise,
#                     mobile=mobile,
#                     email=email,
#                     dob=dob if pd.notnull(dob) else None,
#                     date_of_anniversary=date_of_anniversary if pd.notnull(date_of_anniversary) else None,
#                     address=address,
#                     pincode=pincode,
#                     city=city,
#                     state=state,
#                     pan_card_number=pan_card_number,
#                     aadhar_no=aadhar_no,
#                     referral_code=generate_referral_code(),
#                     created_at=now(),
#                     updated_at=now(),
#                 )

#             messages.success(request, "Bulk upload successful.")
#         except Exception as e:
#             messages.error(request, f"Error during upload: {str(e)}")

#         return redirect('referral-management')
#         # print("Rendering bulk upload page")  
#     return render(request, 'referral/ref-upload_excel.html')


def refBulkUpload(request): 

    if not request.user.is_authenticated or request.user.is_active != 1:
        messages.error(request, "Please Login First")
        return redirect('login')
    
    # if request.method == "POST":
    #     print("POST request received")  # Debug log

    #     file = request.FILES.get("file")

    if request.method == "POST" and request.FILES.get("file"):
        file = request.FILES["file"]

        if not file:
            messages.error(request,"No file is uploaded")
            return redirect('referral-bulk-upload')
        elif not file.name.endswith((".xlsx",".xls")):
            messages.error(request, "Invalid file type. Please upload an Excel file or .xlxs and .xls extension file allowed")
            return redirect('referral-bulk-upload')
        elif  file.size > 5 * 1024 * 1024:
             messages.error(request,"File is to large. Only 5MB size allowed")
             return redirect('referral-bulk-upload')

        try:
            # Read file to get row count
            wb = openpyxl.load_workbook(file, data_only=True)
            sheet = wb.active
            total_rows = sheet.max_row - 1  # Assuming first row is header
            
            print(f"Total Rows Found: {total_rows}")
        except Exception as e:
            print(f"Excel read error: {e}")
            messages.error(request, f"Error reading Excel file: {str(e)}")
            return redirect('referral-management')

        try:
            # file.seek(0)  # Reset pointer
            

            excel_instance = RefUploadedExcel.objects.create(
                file=file,
                created_by=request.user,

                total_rows=total_rows
            )

            # Save file name and URL now that file is stored
            excel_instance.file_name = file.name
            excel_instance.file_url = excel_instance.file.url
            excel_instance.save()

            # Uncomment only if async is properly configured
            # Trigger async task
            print(f"Triggering task for file ID {excel_instance.id}")
            async_task('empPortal.taskz.referral_task.refBulkUpload', excel_instance.id)
            # print("Excel instance saved and task triggered.")

            messages.success(request, "Excel uploaded successfully. Processing started in Background")

        except Exception as e:
            print(f"Upload error: {e}")
            messages.error(request, f"Error during upload: {str(e)}")

        return redirect('referral-bulk-upload')

    return render(request, 'referral/ref-upload_excel.html')

@login_required
def soft_delete_referral(request, pk):
    referral = get_object_or_404(Referral, pk=pk)
    
    # Convert invalid empty strings to None
    if referral.dob == "":
        referral.dob = None
    if referral.date_of_anniversary == "":
        referral.date_of_anniversary = None

    # Mark as deleted
    referral.referral_is_delete = True
    referral.referral_deleted_by = request.user
    referral.save()
    return redirect('referral-management')



        
