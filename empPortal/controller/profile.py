from django.http import HttpResponse
from django.contrib.auth.hashers import make_password
from django.contrib.auth import update_session_auth_hash
from django.shortcuts import render,redirect, get_object_or_404
from django.contrib import messages
from django.template import loader
from ..models import Commission,Users,Branch, DocumentUpload, ExamResult,BqpMaster
from empPortal.model import BankDetails
from ..forms import DocumentUploadForm
from django.contrib.auth import authenticate, login ,logout
from django.core.files.storage import FileSystemStorage
import re
from django.db import IntegrityError
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
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db import connection

from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

from django.views.decorators.csrf import csrf_exempt
from pprint import pprint 
import pdfkit
from django.templatetags.static import static  # ✅ Import static
from django.template.loader import render_to_string
from ..helpers import sync_user_to_partner, update_partner_by_user_id

OPENAI_API_KEY = settings.OPENAI_API_KEY

app = FastAPI()

# views.py
from django.http import JsonResponse
from ..utils import send_sms_post
from django.http import HttpResponseBadRequest




def update_profile_image(request):
    if not request.user.is_authenticated:
        return redirect('login')
    
    if request.method == 'POST' and request.FILES.get('profile_image'):
        uploaded_file = request.FILES['profile_image']
        user = request.user  # Should be an instance of Users

        try:
            # Define the relative path where the image will be saved
            filename = f"user_{user.id}_{uploaded_file.name}"
            relative_path = os.path.join('uploads/profile_images/', filename)

            # Save the file using relative path only
            file_path = default_storage.save(relative_path, uploaded_file)

            # Update user model with the file path
            user.profile_image = file_path
            user.save(update_fields=['profile_image'])

            messages.success(request, 'Profile image updated successfully.')
        except Exception as e:
            messages.error(request, f"Error updating profile image: {str(e)}")

        return redirect('my-account')
    
    messages.error(request, "Error updating profile image")
    return redirect('my-account')





def send_sms_view(request):
    phone_number = request.GET.get("number", "918709620029")  # Default for testing
    message = request.GET.get("message", "Hello! This is a test SMS.")

    response = send_sms_post(phone_number, message)  # or send_sms_post(phone_number, message)

    return JsonResponse(response)


def dictfetchall(cursor):
    "Returns all rows from a cursor as a dict"
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

def myAccount(request):
    if request.user.is_authenticated:
        # send_sms_view(request)
        # Fetch user and bank details for the logged-in user
        user_details = Users.objects.get(id=request.user.id)  # Fetching the user's details
        bank_details = BankDetails.objects.filter(user_id=request.user.id).first()  # Fetching bank details

        # Get or create document instance for user
        docs = DocumentUpload.objects.filter(user_id=request.user.id).first()
        # Fetch commissions for the specific member
        query = """
            SELECT c.*, u.first_name, u.last_name, c.product_id
            FROM commissions c
            INNER JOIN users u ON c.member_id = u.id
            WHERE c.member_id = %s
        """
        
        with connection.cursor() as cursor:
            cursor.execute(query, [request.user.id])
            commissions_list = dictfetchall(cursor)


        document_fields = [
            ("aadhaar_card_front", "Aadhaar Card Front", "aadhar-front.jpg"),
            ("aadhaar_card_back", "Aadhaar Card Back", "aadhar-back.jpg"),
            ("upload_pan", "PAN Card", "pan-card.webp"),
            ("upload_cheque", "Cancelled Cheque", "cancel-cheque.jpg"),
            ("tenth_marksheet", "10th Marksheet", "default-marksheet.jpg"),
        ]
        # Define available products
        products = [
            {'id': 1, 'name': 'Motor'},
            {'id': 2, 'name': 'Health'},
            {'id': 3, 'name': 'Term'},
        ]

        # Ensure dictionary uses integer keys
        product_dict = {product['id']: product['name'] for product in products}

        # Map product names to commissions list
        for commission in commissions_list:
            product_id = commission.get('product_id')
            commission['product_name'] = product_dict.get(int(product_id), 'Unknown') if product_id is not None else 'Unknown'

        branches = Branch.objects.all().order_by('-created_at')

        manager_list = []
        branch = None
        if user_details.branch_id:
            branch = Branch.objects.filter(id=user_details.branch_id).first()
            managers = Users.objects.filter(branch_id=user_details.branch_id, role_id=2)
            manager_list = [{'id': m.id, 'full_name': f'{m.first_name} {m.last_name}'} for m in managers]
                
        rm = None
        if user_details.senior_id:
            rm = Users.objects.filter(id=user_details.senior_id).first()

        rm_list = []
        tl = None
        if rm and rm.senior_id:
            rms = Users.objects.filter(senior_id=rm.senior_id, role_id=5)
            rm_list = [{'id': r.id, 'full_name': f'{r.first_name} {r.last_name}'} for r in rms]
            tl = Users.objects.filter(id=rm.senior_id).first()

        manager = None
        tl_list = []

        if tl and tl.senior_id: 
            tls = Users.objects.filter(senior_id=tl.senior_id, role_id=3)
            tl_list = [{'id': t.id, 'full_name': f'{t.first_name} {t.last_name}'} for t in tls]
            manager = Users.objects.filter(id=tl.senior_id).first()

        exam_details = None
        if request.user.exam_attempt > 0:
            try:
                exam_details = ExamResult.objects.filter(user_id=request.user.id).latest('created_at')
            except ExamResult.DoesNotExist:
                exam_details = None
                
        return render(request, 'profile/my-account.html', {
            'user_details': user_details,
            'bank_details': bank_details,
            'products': products,
            'manager_list': manager_list,
            'rm_list': rm_list,
            'tl_list': tl_list,
            'branches': branches,
            'rm_details': rm,
            'tl_details': tl,
            'branch': branch,
            'manager_details': manager,
            'commissions': commissions_list , 
            'document_fields': document_fields , 
            'docs': docs ,
            'exam_details':exam_details
        })
    else:
        return redirect('login')


def update_user_details(request):
    if request.method == 'POST':
        user_details = Users.objects.get(id=request.user.id)
        user_details.first_name = request.POST['first_name']
        user_details.last_name = request.POST['last_name']
        user_details.email = request.POST['email']
        user_details.phone = request.POST['phone']
        user_details.gender = request.POST['gender']
        user_details.dob = request.POST['dob']
        user_details.state = request.POST['state']
        user_details.city = request.POST['city']
        user_details.pincode = request.POST['pincode']
        user_details.address = request.POST['address']
        user_details.save()
        (user_details.id, request)  # Sync user data to Partner model

        messages.success(request, "User details updated successfully!")
        return redirect('my-account')  # Redirect back to the user profile page



def storeAllocation(request):
    if request.method == 'POST':
        user_id = request.POST.get('agent_member_id')
        branch_id = request.POST.get('branch')
        rm_id = request.POST.get('role_rm')
        bqp_id =request.POST.get('bqp') # <-- Get BQP Id

        if not branch_id or not rm_id:
            messages.error(request, "Branch and RM cannot be empty.")
            return redirect('member-view', user_id=user_id)

        user = get_object_or_404(Users, id=user_id)
        user.branch_id = branch_id
        user.senior_id = rm_id  # Store sales_manager_id in senior_id
        user.bqp_id = bqp_id # Save BQP ID ()
        user.save()

        sync_user_to_partner(user.id, request)  # Sync user data to Partner model

        messages.success(request, "Allocation assigned successfully!")
        return redirect('member-view', user_id=user_id)
    
    messages.error(request, "Invalid request method.")
    return redirect('member-view', user_id=user_id)

def storeOrUpdateBankDetails(request):
    if request.method == "POST" and request.user.id:
        user_id = request.user.id  # Get the logged-in user's ID
        account_number = request.POST.get('account_number')

        try:
            # Check if bank details already exist for the user
            bank_details, created = BankDetails.objects.get_or_create(user_id=user_id)

            # Check if another user has the same account number
            if BankDetails.objects.filter(account_number=account_number).exclude(user_id=user_id).exists():
                messages.error(request, "This account number is already registered with another user.")
                return redirect('my-account')

            # Update the bank details
            bank_details.account_holder_name = request.POST.get('account_holder_name')
            bank_details.re_enter_account_number = request.POST.get('re_enter_account_number')
            bank_details.account_number = account_number
            bank_details.ifsc_code = request.POST.get('ifsc_code')
            bank_details.city = request.POST.get('city')
            bank_details.state = request.POST.get('state')

            # Save changes
            bank_details.save()
            messages.success(request, "Bank details have been updated successfully.")
        
        except IntegrityError:
            messages.error(request, "An error occurred while saving your bank details. Please try again.")
        
        return redirect('my-account')
    else: 
        return redirect('my-account')

    # If not a POST request, redirect to my-account
    
def check_account_number(request):
    if request.method == "POST":
        account_number = request.POST.get("account_number", "").strip()
        print(f"Checking account number: {account_number}")  # Debugging

        if request.user.is_authenticated:
            user_bank = BankDetails.objects.filter(user_id=request.user.id).first()
            if user_bank and user_bank.account_number == account_number:
                return JsonResponse({"exists": False})  # Allow current user to keep the same account number

        exists = BankDetails.objects.filter(account_number=account_number).exists()
        print(f"Exists in DB: {exists}")  # Debugging

        return JsonResponse({"exists": exists})

    return JsonResponse({"error": "Invalid request"}, status=400)


def upload_documents(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method."}, status=405)

    form = DocumentUploadForm(request.POST, request.FILES)
    
    if not form.is_valid():
        return JsonResponse({"error": "Invalid form submission.", "errors": form.errors}, status=400)

    user_id = request.user.id
    aadhaar_number = form.cleaned_data.get("aadhaar_number")
    pan_number = form.cleaned_data.get("pan_number")
    cheque_number = form.cleaned_data.get("cheque_number")
    role_no = form.cleaned_data.get("role_no")

    # Aadhaar validation (12-digit numeric)
    if aadhaar_number and not re.fullmatch(r"^\d{12}$", aadhaar_number):
        return JsonResponse({"errors": {"aadhaar_number": "Aadhaar must be exactly 12 digits."}}, status=400)

    # PAN validation (Format: 5 letters, 4 numbers, 1 letter)
    if pan_number and not re.fullmatch(r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$", pan_number):
        return JsonResponse({"errors": {"pan_number": "PAN must be in the format ABCDE1234F."}}, status=400)

    # Get or create document record for the user
    existing_doc, created = DocumentUpload.objects.get_or_create(user_id=user_id)

    file_fields = ["aadhaar_card_front", "aadhaar_card_back", "upload_pan", "upload_cheque", "tenth_marksheet"]
    allowed_types = ["image/jpeg", "image/png", "application/pdf"]
    max_file_size = 5 * 1024 * 1024  # 5MB
    files_uploaded = []
    errors = {}

    # Update document details
    existing_doc.aadhaar_number = aadhaar_number
    existing_doc.pan_number = pan_number
    existing_doc.cheque_number = cheque_number
    existing_doc.role_no = role_no

    # Process file uploads with validation
    for field in file_fields:
        uploaded_file = request.FILES.get(field)
        if uploaded_file:
            # Validate file size
            if uploaded_file.size > max_file_size:
                errors[field] = f"{field.replace('_', ' ').title()} exceeds 5MB size limit."
                continue
            
            # Validate file type
            if uploaded_file.content_type not in allowed_types:
                errors[field] = f"{field.replace('_', ' ').title()} must be a JPG, PNG, or PDF file."
                continue

            # Save the valid file
            setattr(existing_doc, field, uploaded_file)
            files_uploaded.append(field.replace("_", " ").title())

    # If there are validation errors, return them
    if errors:
        return JsonResponse({"errors": errors}, status=400)
    
    update_partner_by_user_id(user_id, {"partner_status": "1", "doc_status": '1'}, request=request)

    # Save only if there are updates
    if files_uploaded:
        existing_doc.save()
        return JsonResponse({
            "message": f"Successfully uploaded: {', '.join(files_uploaded)}",
            "reload": True  # Flag for frontend to reload page
        }, status=200)

    return JsonResponse({"message": "No new files were uploaded."}, status=200)



def update_document(request):
    if request.method == "POST" and request.FILES.get("document_file"):
        user_id = request.user.id  # Get current user ID
        document_type = request.POST.get("document_type")  # e.g., 'aadhaar_card_front'

        if document_type not in ["aadhaar_card_front", "aadhaar_card_back", "upload_pan", "upload_cheque", "tenth_marksheet"]:
            return JsonResponse({"error": "Invalid document type"}, status=400)

        uploaded_file = request.FILES["document_file"]

        # Validate file size (Max: 5MB)
        if uploaded_file.size > 5 * 1024 * 1024:
            return JsonResponse({"error": f"{document_type.replace('_', ' ').title()} exceeds 5MB size limit."}, status=400)

        # Validate file type
        allowed_types = ["image/jpeg", "image/png", "application/pdf"]
        if uploaded_file.content_type not in allowed_types:
            return JsonResponse({"error": f"{document_type.replace('_', ' ').title()} must be a JPG, PNG, or PDF file."}, status=400)

        # Get or create the user's document record
        user_doc, created = DocumentUpload.objects.get_or_create(user_id=user_id)
        # Save the new file
        setattr(user_doc, document_type, uploaded_file)
        user_doc.save()
        # Get the correct URL for the uploaded file
        document_field = getattr(user_doc, document_type, None)

        if document_field and hasattr(document_field, "url"):
            new_image_url = request.build_absolute_uri(document_field.url)
        else:
            new_image_url = None  # Handle case where file isn't uploaded

        update_partner_by_user_id(user_id, {"partner_status": "1", "doc_status": '1'}, request=request)

        return JsonResponse({"message": f"{document_type.replace('_', ' ').title()} updated successfully!", "new_image_url": new_image_url})
    
    return JsonResponse({"error": "Invalid request"}, status=400)


def update_document_id(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            user_id = data.get("user_id")
            document_type = data.get("document_type")
            document_number = data.get("document_number")

            # Fetch the document entry for the user
            document = DocumentUpload.objects.filter(user_id=user_id).first()

            if not document:
                return JsonResponse({"success": False, "message": "Document not found."}, status=404)

            # Update the respective document field
            if document_type == "aadhaar":
                document.aadhaar_number = document_number
            elif document_type == "pan":
                document.pan_number = document_number
            elif document_type == "cheque":
                document.cheque_number = document_number
            elif document_type == "role":
                document.role_no = document_number
            else:
                return JsonResponse({"success": False, "message": "Invalid document type."}, status=400)

            document.save()
            return JsonResponse({"success": True, "message": "Document number updated successfully."})

        except json.JSONDecodeError:
            return JsonResponse({"success": False, "message": "Invalid JSON format."}, status=400)
        except Exception as e:
            return JsonResponse({"success": False, "message": str(e)}, status=500)

    return JsonResponse({"success": False, "message": "Invalid request method."}, status=405)



def downloadCertificatePdf(request, cus_id):
    if not request.user.is_authenticated:
        return redirect('login')

    wkhtml_path = os.getenv('WKHTML_PATH', r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe')
    config = pdfkit.configuration(wkhtmltopdf=wkhtml_path)

    # Fetch customer and vehicle details
    user_details = Users.objects.get(id=cus_id)  # Fetching the user's details

    # Data to pass to the template
    context = {
        "user_details": user_details,
        "logo_url": request.build_absolute_uri(static('dist/img/logo2.png'))
    }

    # Render HTML template with context data
    html_content = render_to_string("profile/broker-certificate.html", context)

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