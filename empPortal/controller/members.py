from django.http import HttpResponse
from django.contrib.auth.hashers import make_password
from django.contrib.auth import update_session_auth_hash
from django.shortcuts import render,redirect, get_object_or_404
from django.contrib import messages
from django.template import loader
from ..models import Commission, ExamResult,Users, DocumentUpload, Branch,BqpMaster
from empPortal.model import BankDetails
from django.utils.timezone import localtime
from datetime import datetime
from empPortal.util.context_processors import company_constants
from ..forms import DocumentUploadForm
from django.core.mail import send_mail
from django.core.mail import EmailMessage
from django.utils.timezone import now
from django.contrib.auth import authenticate, login ,logout
from django.core.files.storage import FileSystemStorage
import re
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
import logging
logger = logging.getLogger(__name__)
import pdfkit
from django.template.loader import render_to_string
from pprint import pprint 
from django.db.models import Q
from django.core.paginator import Paginator

from django.db.models.functions import Concat
from django.db.models import Q, Value
from django.contrib.auth.hashers import make_password
import datetime
import re
import pandas as pd
from django.contrib.auth.hashers import make_password
import openpyxl
from dateutil import parser  
from ..models import PartnerUploadExcel
from django.core.files.storage import default_storage
OPENAI_API_KEY = settings.OPENAI_API_KEY
from django.shortcuts import redirect
from django.contrib import messages
import openpyxl
from django.contrib.auth.decorators import login_required
from django_q.tasks import async_task
app = FastAPI()
from empPortal.model import Partner
from ..helpers import sync_user_to_partner, update_partner_by_user_id
from django.db.models import Count
from django.db import models

def dictfetchall(cursor):
    "Returns all rows from a cursor as a dict"
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

from django.db.models import Sum




def partnerCounters():
    # 1) Filter out inactive partners up front
    partners = Partner.objects.exclude(active=0).annotate(
        doc_upload_count=Count('id', filter=Q(partner_status='1', doc_status=1)),
        pending_doc_count =Count('id', filter=Q(partner_status='1', doc_status=2)),
    )

    # 2) Aggregate on that already-filtered queryset
    counters = partners.aggregate(
        total                 = Count('id'),
        requested             = Count('id', filter=Q(partner_status='0')),
        document_verification = Count('id', filter=Q(partner_status='1')),
        in_training           = Count('id', filter=Q(partner_status='2')),
        in_exam               = Count('id', filter=Q(partner_status='3')),
        activated             = Count('id', filter=Q(partner_status='4')),
        inactive              = Count('id', filter=Q(partner_status='5')),
        rejected              = Count('id', filter=Q(partner_status='6')),
        doc_upload            = Sum('doc_upload_count'),
        pending_docs          = Sum('pending_doc_count'),
    )

    return counters

from django.utils.timezone import now

def update_partner_status():
    users = Users.objects.all()

    for user in users:
        docs = DocumentUpload.objects.filter(user_id=user.id)

        if not docs.exists():
            Partner.objects.filter(user_id=user.id).update(doc_status='0', partner_status='0')
            continue

        all_approved = all(
            doc.aadhaar_card_front_status == 'Approved' and
            doc.aadhaar_card_back_status == 'Approved' and
            doc.upload_pan_status == 'Approved' and
            doc.upload_cheque_status == 'Approved' and
            doc.tenth_marksheet_status == 'Approved'
            for doc in docs
        )

        any_pending = any(
            doc.aadhaar_card_front_status == 'Pending' or
            doc.aadhaar_card_back_status == 'Pending' or
            doc.upload_pan_status == 'Pending' or
            doc.upload_cheque_status == 'Pending' or
            doc.tenth_marksheet_status == 'Pending'
            for doc in docs
        )

        # Set doc_status only if documents exist
        if all_approved:
            doc_status = '3'
        elif any_pending:
            doc_status = '2'
        else:
            doc_status = '1'

        # Update doc_status in Partner
        Partner.objects.filter(user_id=user.id).exclude(active=0).update(doc_status=doc_status)

        # Handle partner_status
        if all_approved:
            exam_result = ExamResult.objects.filter(user_id=user.id).first()
            if exam_result:
                if exam_result.status.lower() == 'passed':
                    partner_status = '4'  # Exam passed
                else:
                    partner_status = '3'  # Exam attempted but not passed
            else:
                partner_status = '2'  # Exam not attempted
        elif any_pending:
            partner_status = '1'
        else:
            partner_status = '1'

        Partner.objects.filter(user_id=user.id).update(partner_status=partner_status)

from datetime import timedelta
from django.utils import timezone
from django.db import transaction


def update_exam_eligible_status():
    cutoff = timezone.now() - timedelta(days=5)

    # 1) Find all partner user_ids whose training_start_date is at least 5 days ago.
    partners_qs = Partner.objects.filter(
        partner_status='2',
        training_start_date__lte=cutoff
    )

    eligible_user_ids = partners_qs.values_list('user_id', flat=True).distinct()


    with transaction.atomic():
        # 2) Update Users in bulk
        users_qs = (
            Users.objects
                 .filter(
                     id__in=eligible_user_ids,
                     activation_status='1',
                     exam_eligibility=0,
                     exam_attempt__lt=3,
                 )
                 .exclude(exam_pass=1)
        )
        updated_users = users_qs.update(exam_eligibility=1)

        # 3) Update their Partners' status
        # Only affects partners whose user_id was in eligible_user_ids
        updated_partners = (
            Partner.objects
                   .filter(user_id__in=eligible_user_ids)
                   .update(partner_status='3')
        )

    return {
        'users_marked_eligible': updated_users,
        'partners_activated':    updated_partners,
    }

def members(request):
    if not request.user.is_authenticated:
        return redirect('login')
    
    update_exam_eligible_status()
    
    user = request.user

    if user.role_id == 1 or str(user.department_id) in ["1","2"]:    #admin and sales dept view only
        role_ids = [4]  # Filter for specific roles

        per_page = request.GET.get('per_page', 10)
        search_field = request.GET.get('search_field', '')  # Field to search
        search_query = request.GET.get('search_query', '')  # Search value
        sorting = request.GET.get('sorting', '')  # Sorting option
        global_search = request.GET.get('global_search', '').strip()
        
        try:
            per_page = int(per_page)
        except ValueError:
            per_page = 10  # Default to 10 if invalid value is given

        # Base QuerySet
        users = Users.objects.filter(role_id__in=role_ids)

                
        for user in users:
            if not Partner.objects.filter(user_id=user.id).exists():
                sync_user_to_partner(user.id, request)

        if global_search:
            users = users.annotate(
                search_full_name=Concat('first_name', Value(' '), 'last_name')
            ).filter(
                Q(search_full_name__icontains=global_search) |  
                Q(first_name__icontains=global_search) |
                Q(last_name__icontains=global_search) |
                Q(email__icontains=global_search) |
                Q(phone__icontains=global_search)  
            )

        partners = Partner.objects.exclude(active=0)  # Status '2' represents training
        partner_ids = partners.values_list('user_id', flat=True)  # Get user IDs

        # Base QuerySet: Users who are in training (partner_status='2')
        users = Users.objects.filter(id__in=partner_ids)

    # Get filter values from GET request
        user_gen_id = request.GET.get('user_gen_id', '').strip()
        user_name = request.GET.get('user_name', '').strip() #Apply filter based on full name column not 1st & last name
        email = request.GET.get('email', '').strip()
        phone = request.GET.get('phone', '').strip()
        pan_no = request.GET.get('pan_no', '').strip()  

    # Apply filters
        if user_gen_id:
            users = users.filter(user_gen_id__icontains=user_gen_id)
        if user_name:
            users = users.filter(user_name__icontains=user_name)
        if email:
            users = users.filter(email__icontains=email)
        if phone:
            users = users.filter(phone__icontains=phone)
        if pan_no:
            users = users.filter(pan_no__icontains=pan_no)

        # Apply sorting
        if sorting == "name_a_z":
            users = users.order_by("first_name")
        elif sorting == "name_z_a":
            users = users.order_by("-first_name")
        elif sorting == "recently_activated":
            users = users.filter(activation_status='1').order_by("-updated_at")
        elif sorting == "recently_deactivated":
            users = users.filter(
                Q(activation_status='0') | Q(activation_status__isnull=True) | Q(activation_status='')
            ).order_by("-updated_at")
        else:
            users = users.order_by("-updated_at")

        # Exam Result
        examresult = ExamResult.objects.filter(user=request.user) # or .first()
        inexam = True if examresult else False
 

        
        total_agents = Users.objects.filter(role_id__in=role_ids).count()
        active_agents = Users.objects.filter(role_id__in=role_ids,activation_status='1').count()
        deactive_agents = Users.objects.filter(
            role_id__in=role_ids
        ).exclude(
            activation_status='1'
        ).count()
        pending_agents = 0  # Define pending logic if needed

        # Paginate results
        paginator = Paginator(users, per_page)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        counters = partnerCounters()
        return render(request, 'members/members.html', {
            'page_obj': page_obj,
            'total_agents': total_agents,
            'counters': counters,
            'active_agents': active_agents,
            'deactive_agents': deactive_agents,
            'pending_agents': pending_agents,
            'search_field': search_field,
            'search_query': search_query,
            'global_search': global_search,
            'sorting': sorting,
            'per_page': per_page,
            'users': users,
            'inexam': inexam,
            'examresult': examresult , # Pass the exam result to the template
            'members_all': True,
            'members_requested' : False,
        })
    else:
        return redirect('login')
    


def members_requested(request):
    if not request.user.is_authenticated:
        return redirect('login')

    user = request.user

    if user.role_id == 1 or str(user.department_id) in ["1","2"]:
        role_ids = [4]  # Filter for specific roles

        per_page = request.GET.get('per_page', 10)
        search_field = request.GET.get('search_field', '')  # Field to search
        search_query = request.GET.get('search_query', '')  # Search value
        sorting = request.GET.get('sorting', '')  # Sorting option
        global_search = request.GET.get('global_search', '').strip()
        
        try:
            per_page = int(per_page)
        except ValueError:
            per_page = 10  # Default to 10 if invalid value is given

        # Base QuerySet
        users = Users.objects.filter(role_id__in=role_ids).exclude(
            activation_status='1'
        )

        if global_search:
            users = users.annotate(
                search_full_name=Concat('first_name', Value(' '), 'last_name')
            ).filter(
                Q(search_full_name__icontains=global_search) |  
                Q(first_name__icontains=global_search) |
                Q(last_name__icontains=global_search) |
                Q(email__icontains=global_search) |
                Q(phone__icontains=global_search)  
            )

        """# Apply filtering
        if search_field and search_query:
            filter_args = {f"{search_field}__icontains": search_query}
            users = users.filter(**filter_args)"""

        partners = Partner.objects.filter(partner_status='0').exclude(active=0)
        partner_ids = partners.values_list('user_id', flat=True)  # Get user IDs

        users = Users.objects.filter(id__in=partner_ids)

    # Get filter values from GET request
        user_gen_id = request.GET.get('user_gen_id', '').strip()
        user_name = request.GET.get('user_name', '').strip()
        email = request.GET.get('email', '').strip()
        phone = request.GET.get('phone', '').strip()
        pan_no = request.GET.get('pan_no', '').strip()  

    # Apply filters
        if user_gen_id:
            users = users.filter(user_gen_id__icontains=user_gen_id)
        if user_name:
            users = users.filter(user_name__icontains=user_name)
        if email:
            users = users.filter(email__icontains=email)
        if phone:
            users = users.filter(phone__icontains=phone)
        if pan_no:
            users = users.filter(pan_no__icontains=pan_no)

        context = {
            'users': users
         }
        

        # Apply sorting
        if sorting == "name_a_z":
            users = users.order_by("first_name")
        elif sorting == "name_z_a":
            users = users.order_by("-first_name")
        elif sorting == "recently_activated":
            users = users.filter(activation_status='1').order_by("-updated_at")
        elif sorting == "recently_deactivated":
            users = users.filter(
                Q(activation_status='0') | Q(activation_status__isnull=True) | Q(activation_status='')
            ).order_by("-updated_at")
        else:
            users = users.order_by("-updated_at")

        
        total_agents = Users.objects.filter(role_id__in=role_ids).count()
        active_agents = Users.objects.filter(role_id__in=role_ids,activation_status='1').count()
        deactive_agents = Users.objects.filter(
            role_id__in=role_ids
        ).exclude(
            activation_status='1'
        ).count()
        pending_agents = 0  # Define pending logic if needed

        # Paginate results
        paginator = Paginator(users, per_page)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        counters = partnerCounters()

        return render(request, 'members/members-requested.html', {
            'page_obj': page_obj,
            'total_agents': total_agents,
            'active_agents': active_agents,
            'deactive_agents': deactive_agents,
            'counters': counters,
            'partners': partners,
            'pending_agents': pending_agents,
            'search_field': search_field,
            'search_query': search_query,
            'global_search': global_search,
            'sorting': sorting,
            'per_page': per_page,
            'members_all' : False,
        })
    else:
        return redirect('login')   

        
def members_document_pending_upload(request):
    if not request.user.is_authenticated:
        return redirect('login')

    user = request.user

    if user.role_id == 1 or str(user.department_id) in ["1","2"]:
        role_ids = [4]  # Filter for specific roles

        per_page = request.GET.get('per_page', 10)
        search_field = request.GET.get('search_field', '')  # Field to search
        search_query = request.GET.get('search_query', '')  # Search value
        sorting = request.GET.get('sorting', '')  # Sorting option
        global_search = request.GET.get('global_search', '').strip()
        
        try:
            per_page = int(per_page)
        except ValueError:
            per_page = 10  # Default to 10 if invalid value is given

        # Base QuerySet
        users = Users.objects.filter(role_id__in=role_ids).exclude(
            activation_status='1'
        )

        if global_search:
            users = users.annotate(
                search_full_name=Concat('first_name', Value(' '), 'last_name')
            ).filter(
                Q(search_full_name__icontains=global_search) |  
                Q(first_name__icontains=global_search) |
                Q(last_name__icontains=global_search) |
                Q(email__icontains=global_search) |
                Q(phone__icontains=global_search)  
            )

        """# Apply filtering
        if search_field and search_query:
            filter_args = {f"{search_field}__icontains": search_query}
            users = users.filter(**filter_args)"""

        partners = Partner.objects.filter(partner_status='0').exclude(active=0)
        partner_ids = partners.values_list('user_id', flat=True)  # Get user IDs

        users = Users.objects.filter(id__in=partner_ids)

    # Get filter values from GET request
        user_gen_id = request.GET.get('user_gen_id', '').strip()
        user_name = request.GET.get('user_name', '').strip()
        email = request.GET.get('email', '').strip()
        phone = request.GET.get('phone', '').strip()
        pan_no = request.GET.get('pan_no', '').strip()  

    # Apply filters
        if user_gen_id:
            users = users.filter(user_gen_id__icontains=user_gen_id)
        if user_name:
            users = users.filter(user_name__icontains=user_name)
        if email:
            users = users.filter(email__icontains=email)
        if phone:
            users = users.filter(phone__icontains=phone)
        if pan_no:
            users = users.filter(pan_no__icontains=pan_no)

        context = {
            'users': users
         }
        

        # Apply sorting
        if sorting == "name_a_z":
            users = users.order_by("first_name")
        elif sorting == "name_z_a":
            users = users.order_by("-first_name")
        elif sorting == "recently_activated":
            users = users.filter(activation_status='1').order_by("-updated_at")
        elif sorting == "recently_deactivated":
            users = users.filter(
                Q(activation_status='0') | Q(activation_status__isnull=True) | Q(activation_status='')
            ).order_by("-updated_at")
        else:
            users = users.order_by("-updated_at")

        
        total_agents = Users.objects.filter(role_id__in=role_ids).count()
        active_agents = Users.objects.filter(role_id__in=role_ids,activation_status='1').count()
        deactive_agents = Users.objects.filter(
            role_id__in=role_ids
        ).exclude(
            activation_status='1'
        ).count()
        pending_agents = 0  # Define pending logic if needed

        # Paginate results
        paginator = Paginator(users, per_page)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        counters = partnerCounters()

        return render(request, 'members/members-pending-upload.html', {
            'page_obj': page_obj,
            'total_agents': total_agents,
            'active_agents': active_agents,
            'deactive_agents': deactive_agents,
            'counters': counters,
            'partners': partners,
            'pending_agents': pending_agents,
            'search_field': search_field,
            'search_query': search_query,
            'global_search': global_search,
            'sorting': sorting,
            'per_page': per_page,
            'members_all' : False,
        })
    else:
        return redirect('login')    

    
def posTrainingCertificate(request, user_id):
    if not request.user.is_authenticated:
        return redirect('login')

    # Get wkhtmltopdf binary path from environment or settings
    wkhtml_path = os.getenv('WKHTML_PATH', getattr(settings, 'WKHTML_PATH', r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'))
    config = pdfkit.configuration(wkhtmltopdf=wkhtml_path)

    customer = get_object_or_404(Users, id=user_id)
    partner = get_object_or_404(Partner, user_id=user_id)

    # Resolve profile image path or default image
    if customer.profile_image:
        profile_image_path = default_storage.path(customer.profile_image.name)
        profile_image_url = profile_image_path if os.path.exists(profile_image_path) else os.path.join(settings.BASE_DIR, getattr(settings, 'DEFAULT_POS_IMAGE', 'empPortal/static/dist/img/default-image-pos.jpg'))
    else:
        profile_image_url = os.path.join(settings.BASE_DIR, getattr(settings, 'DEFAULT_POS_IMAGE', 'empPortal/static/dist/img/default-image-pos.jpg'))

    docs = DocumentUpload.objects.filter(user_id=user_id).first()

    context = {
        "partner": partner,
        "docs": docs,
        "customer": customer,
        "logo_url": os.path.join(settings.BASE_DIR, getattr(settings, 'LOGO_WITH_EMP_PORTAL', 'empPortal/static/dist/img/logo2.png')),
        "signature_elevate": os.path.join(settings.BASE_DIR, getattr(settings, 'SIGNATURE_ELEVATE', 'empPortal/static/dist/img/elevate-signature.png')),
        "default_image_pos": profile_image_url,
        "signature_pos": os.path.join(settings.BASE_DIR, getattr(settings, 'SIGNATURE_POS', 'empPortal/static/dist/img/signature-pos.webp')),
    }

    # 🔥 Add this to manually include context processor variables
    context.update(company_constants(request))
    html_content = render_to_string("members/download-training-certificate.html", context)

    options = {
        'enable-local-file-access': '',
        'page-size': 'A4',
        'encoding': "UTF-8",
    }

    pdf = pdfkit.from_string(html_content, False, configuration=config, options=options)

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="training_certificate_20250{user_id}.pdf"'

    return response


from django.core.files.storage import default_storage
from django.conf import settings
import os

def posCertificate(request, user_id):
    if not request.user.is_authenticated:
        return redirect('login')

    wkhtml_path = os.getenv('WKHTML_PATH', getattr(settings, 'WKHTML_PATH', r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'))
    config = pdfkit.configuration(wkhtmltopdf=wkhtml_path)

    customer = get_object_or_404(Users, id=user_id)
    docs = DocumentUpload.objects.filter(user_id=user_id).first()
    passed_date = customer.examRes.created_at if hasattr(customer, 'examRes') else None

    # Determine profile image path or fallback to default
    if customer.profile_image:
        profile_image_path = default_storage.path(customer.profile_image.name)
        profile_image_url = profile_image_path if os.path.exists(profile_image_path) else os.path.join(settings.BASE_DIR, getattr(settings, 'DEFAULT_POS_IMAGE', 'empPortal/static/dist/img/default-image-pos.jpg'))
    else:
        profile_image_url = os.path.join(settings.BASE_DIR, getattr(settings, 'DEFAULT_POS_IMAGE', 'empPortal/static/dist/img/default-image-pos.jpg'))

    context = {
        "customer": customer,
        "passed_date": passed_date,
        "docs": docs,
        "logo_url": os.path.join(settings.BASE_DIR, getattr(settings, 'LOGO_WITH_EMP_PORTAL', 'empPortal/static/dist/img/logo2.png')),
        "signature_elevate": os.path.join(settings.BASE_DIR, getattr(settings, 'SIGNATURE_ELEVATE', 'empPortal/static/dist/img/elevate-signature.png')),
        "profile_image_url": profile_image_url,
        "signature_pos": os.path.join(settings.BASE_DIR, getattr(settings, 'SIGNATURE_POS', 'empPortal/static/dist/img/signature-pos.webp')),
    }
    context.update(company_constants(request))

    html_content = render_to_string("members/download-certificate.html", context)

    options = {
        'enable-local-file-access': '',
        'page-size': 'A4',
        'encoding': "UTF-8",
    }

    pdf = pdfkit.from_string(html_content, False, configuration=config, options=options)

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="pos_certificate_20250{user_id}.pdf"'

    return response





def members_inprocess(request):
    if not request.user.is_authenticated:
        return redirect('login')

    user = request.user

    if user.role_id == 1 or str(user.department_id) in ["1","2"]:
        role_ids = [4]  # Filter for specific roles

        per_page = request.GET.get('per_page', 10)
        search_field = request.GET.get('search_field', '')  # Field to search
        search_query = request.GET.get('search_query', '')  # Search value
        sorting = request.GET.get('sorting', '')  # Sorting option
        global_search = request.GET.get('global_search', '').strip()
        
        try:
            per_page = int(per_page)
        except ValueError:
            per_page = 10  # Default to 10 if invalid value is given

        # Base QuerySet
        # users = Users.objects.filter(role_id__in=role_ids, activation_status=4)

                
        partners = Partner.objects.filter(
            Q(partner_status='1') | Q(doc_status__gte=1)
        )
        partner_ids = partners.values_list('user_id', flat=True)  # Get user IDs

        users = Users.objects.filter(id__in=partner_ids)
        
        if global_search:
            users = users.annotate(
                search_full_name=Concat('first_name', Value(' '), 'last_name')
            ).filter(
                Q(search_full_name__icontains=global_search) |  
                Q(first_name__icontains=global_search) |
                Q(last_name__icontains=global_search) |
                Q(email__icontains=global_search) |
                Q(phone__icontains=global_search)  
            )

        # Apply filtering
        # if search_field and search_query:
        #     filter_args = {f"{search_field}__icontains": search_query}
        #     users = users.filter(**filter_args)
         # Apply filtering
        if 'user_gen_id' in request.GET and request.GET['user_gen_id']:
            users = users.filter(user_gen_id__icontains=request.GET['user_gen_id'])
        if 'user_name' in request.GET and request.GET['user_name']:
            users = users.filter(user_name__icontains=request.GET['user_name'])
        if 'pan_no' in request.GET and request.GET['pan_no']:
            users = users.filter(pan_no__icontains=request.GET['pan_no'])
        if 'email' in request.GET and request.GET['email']:
            users = users.filter(email__icontains=request.GET['email'])
        if 'phone' in request.GET and request.GET['phone']:
            users = users.filter(phone__icontains=request.GET['phone'])

        # Apply sorting
        if sorting == "name_a_z":
            users = users.order_by("first_name")
        elif sorting == "name_z_a":
            users = users.order_by("-first_name")
        elif sorting == "recently_activated":
            users = users.filter(activation_status='1').order_by("-updated_at")
        elif sorting == "recently_deactivated":
            users = users.filter(
                Q(activation_status='0') | Q(activation_status__isnull=True) | Q(activation_status='')
            ).order_by("-updated_at")
        else:
            users = users.order_by("-updated_at")

        
        total_agents = Users.objects.filter(role_id__in=role_ids).count()
        active_agents = Users.objects.filter(role_id__in=role_ids,activation_status='1').count()
        
        deactive_agents = Users.objects.filter(
            role_id__in=role_ids
        ).exclude(
            activation_status='1'
        ).count()
        pending_agents = 0  # Define pending logic if needed

        # Paginate results
        paginator = Paginator(users, per_page)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        counters = partnerCounters()

        return render(request, 'members/members-inprocess.html', {
            'page_obj': page_obj,
            'total_agents': total_agents,
            'counters': counters,
            'active_agents': active_agents,
            'deactive_agents': deactive_agents,
            'pending_agents': pending_agents,
            'search_field': search_field,
            'search_query': search_query,
            'global_search': global_search,
            'sorting': sorting,
            'per_page': per_page,
        })
    else:
        return redirect('login')
    
def members_document_upload(request):
    if not request.user.is_authenticated:
        return redirect('login')

    
    user = request.user

    if user.role_id == 1 or str(user.department_id) in ["1","2"]:
        role_ids = [4]  # Filter for specific roles

        per_page = request.GET.get('per_page', 10)
        search_field = request.GET.get('search_field', '')  # Field to search
        search_query = request.GET.get('search_query', '')  # Search value
        sorting = request.GET.get('sorting', '')  # Sorting option
        global_search = request.GET.get('global_search', '').strip()
        
        try:
            per_page = int(per_page)
        except ValueError:
            per_page = 10  # Default to 10 if invalid value is given

        # Base QuerySet
        # users = Users.objects.filter(role_id__in=role_ids, activation_status=4)

                
        partners = Partner.objects.filter(
            Q(doc_status='1') | Q(doc_status=1)
        ).exclude(active=0)
        partner_ids = partners.values_list('user_id', flat=True)  # Get user IDs

        users = Users.objects.filter(id__in=partner_ids)
        
        if global_search:
            users = users.annotate(
                search_full_name=Concat('first_name', Value(' '), 'last_name')
            ).filter(
                Q(search_full_name__icontains=global_search) |  
                Q(first_name__icontains=global_search) |
                Q(last_name__icontains=global_search) |
                Q(email__icontains=global_search) |
                Q(phone__icontains=global_search)  
            )

        # Apply filtering
        # if search_field and search_query:
        #     filter_args = {f"{search_field}__icontains": search_query}
        #     users = users.filter(**filter_args)
         # Apply filtering
        if 'user_gen_id' in request.GET and request.GET['user_gen_id']:
            users = users.filter(user_gen_id__icontains=request.GET['user_gen_id'])
        if 'user_name' in request.GET and request.GET['user_name']:
            users = users.filter(user_name__icontains=request.GET['user_name'])
        if 'pan_no' in request.GET and request.GET['pan_no']:
            users = users.filter(pan_no__icontains=request.GET['pan_no'])
        if 'email' in request.GET and request.GET['email']:
            users = users.filter(email__icontains=request.GET['email'])
        if 'phone' in request.GET and request.GET['phone']:
            users = users.filter(phone__icontains=request.GET['phone'])

        # Apply sorting
        if sorting == "name_a_z":
            users = users.order_by("first_name")
        elif sorting == "name_z_a":
            users = users.order_by("-first_name")
        elif sorting == "recently_activated":
            users = users.filter(activation_status='1').order_by("-updated_at")
        elif sorting == "recently_deactivated":
            users = users.filter(
                Q(activation_status='0') | Q(activation_status__isnull=True) | Q(activation_status='')
            ).order_by("-updated_at")
        else:
            users = users.order_by("-updated_at")

        
        total_agents = Users.objects.filter(role_id__in=role_ids).count()
        active_agents = Users.objects.filter(role_id__in=role_ids,activation_status='1').count()
        
        deactive_agents = Users.objects.filter(
            role_id__in=role_ids
        ).exclude(
            activation_status='1'
        ).count()
        pending_agents = 0  # Define pending logic if needed

        # Paginate results
        paginator = Paginator(users, per_page)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        counters = partnerCounters()

        return render(request, 'members/members-document-upload.html', {
            'page_obj': page_obj,
            'total_agents': total_agents,
            'counters': counters,
            'active_agents': active_agents,
            'deactive_agents': deactive_agents,
            'pending_agents': pending_agents,
            'search_field': search_field,
            'search_query': search_query,
            'global_search': global_search,
            'sorting': sorting,
            'per_page': per_page,
        })
    else:
        return redirect('login')
    
def members_document_inpending(request):
    if not request.user.is_authenticated:
        return redirect('login')

    
    user = request.user

    if user.role_id == 1 or str(user.department_id) in ["1","2"]:
        role_ids = [4]  # Filter for specific roles

        per_page = request.GET.get('per_page', 10)
        search_field = request.GET.get('search_field', '')  # Field to search
        search_query = request.GET.get('search_query', '')  # Search value
        sorting = request.GET.get('sorting', '')  # Sorting option
        global_search = request.GET.get('global_search', '').strip()
        
        try:
            per_page = int(per_page)
        except ValueError:
            per_page = 10  # Default to 10 if invalid value is given

        # Base QuerySet
        # users = Users.objects.filter(role_id__in=role_ids, activation_status=4)

                
        partners = Partner.objects.filter(
            Q(doc_status='2') | Q(doc_status=2)
        ).exclude(active=0)
        partner_ids = partners.values_list('user_id', flat=True)  # Get user IDs

        users = Users.objects.filter(id__in=partner_ids)
        
        if global_search:
            users = users.annotate(
                search_full_name=Concat('first_name', Value(' '), 'last_name')
            ).filter(
                Q(search_full_name__icontains=global_search) |  
                Q(first_name__icontains=global_search) |
                Q(last_name__icontains=global_search) |
                Q(email__icontains=global_search) |
                Q(phone__icontains=global_search)  
            )

        # Apply filtering
        # if search_field and search_query:
        #     filter_args = {f"{search_field}__icontains": search_query}
        #     users = users.filter(**filter_args)
         # Apply filtering
        if 'user_gen_id' in request.GET and request.GET['user_gen_id']:
            users = users.filter(user_gen_id__icontains=request.GET['user_gen_id'])
        if 'user_name' in request.GET and request.GET['user_name']:
            users = users.filter(user_name__icontains=request.GET['user_name'])
        if 'pan_no' in request.GET and request.GET['pan_no']:
            users = users.filter(pan_no__icontains=request.GET['pan_no'])
        if 'email' in request.GET and request.GET['email']:
            users = users.filter(email__icontains=request.GET['email'])
        if 'phone' in request.GET and request.GET['phone']:
            users = users.filter(phone__icontains=request.GET['phone'])

        # Apply sorting
        if sorting == "name_a_z":
            users = users.order_by("first_name")
        elif sorting == "name_z_a":
            users = users.order_by("-first_name")
        elif sorting == "recently_activated":
            users = users.filter(activation_status='1').order_by("-updated_at")
        elif sorting == "recently_deactivated":
            users = users.filter(
                Q(activation_status='0') | Q(activation_status__isnull=True) | Q(activation_status='')
            ).order_by("-updated_at")
        else:
            users = users.order_by("-updated_at")

        
        total_agents = Users.objects.filter(role_id__in=role_ids).count()
        active_agents = Users.objects.filter(role_id__in=role_ids,activation_status='1').count()
        
        deactive_agents = Users.objects.filter(
            role_id__in=role_ids
        ).exclude(
            activation_status='1'
        ).count()
        pending_agents = 0  # Define pending logic if needed

        # Paginate results
        paginator = Paginator(users, per_page)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        counters = partnerCounters()

        return render(request, 'members/members-document-inpending.html', {
            'page_obj': page_obj,
            'total_agents': total_agents,
            'counters': counters,
            'active_agents': active_agents,
            'deactive_agents': deactive_agents,
            'pending_agents': pending_agents,
            'search_field': search_field,
            'search_query': search_query,
            'global_search': global_search,
            'sorting': sorting,
            'per_page': per_page,
        })
    else:
        return redirect('login')
    
# def members_intraining(request):
#     if request.user.is_authenticated:
#     
#             # Define the list of role IDs to filter
#             # role_ids = [2, 3, 4]
#             role_ids = [4]
#             # Filter users whose role_id is in the specified list
#             users = Users.objects.filter(role_id__in=role_ids)
#         else:
#             users = Users.objects.none()  # Return an empty queryset for unauthorized users
#         counters = partnerCounters()

#         partners = Partner.objects.filter(partner_status='2')
#         partner_ids = partners.values_list('user_id', flat=True)  # Get user IDs

#         users = Users.objects.filter(id__in=partner_ids)
        
#         return render(request, 'members/members-intraining.html', {
#             'counters': counters,
#             'users': users
#             })
#     else:
#         return redirect('login')

def members_intraining(request):
    if not request.user.is_authenticated:
        return redirect('login')

    
    user = request.user

    if user.role_id == 1 or str(user.department_id) in ["1","2"]:
        role_ids = [4]  # Filter for specific roles

        per_page = request.GET.get('per_page', 10)
        search_field = request.GET.get('search_field', '')  # Field to search
        search_query = request.GET.get('search_query', '')  # Search value
        sorting = request.GET.get('sorting', '')  # Sorting option
        global_search = request.GET.get('global_search', '').strip()
        
        try:
            per_page = int(per_page)
        except ValueError:
            per_page = 10  # Default to 10 if invalid value is given

        # Get partners in training (assuming status '2' represents training)
        partners = Partner.objects.filter(partner_status='2').exclude(active=0)  # Status '2' represents training
        partner_ids = partners.values_list('user_id', flat=True)  # Get user IDs

        # Base QuerySet: Users who are in training (partner_status='2')
        users = Users.objects.filter(id__in=partner_ids)
        
        if global_search:
            users = users.annotate(
                search_full_name=Concat('first_name', Value(' '), 'last_name')
            ).filter(
                Q(search_full_name__icontains=global_search) |  
                Q(first_name__icontains=global_search) |
                Q(last_name__icontains=global_search) |
                Q(email__icontains=global_search) |
                Q(phone__icontains=global_search)
            )

        # Apply filtering
        # if search_field and search_query:
        #     filter_args = {f"{search_field}__icontains": search_query}
        #     users = users.filter(**filter_args)

         # Apply filtering
        if 'user_gen_id' in request.GET and request.GET['user_gen_id']:
            users = users.filter(user_gen_id__icontains=request.GET['user_gen_id'])
        if 'user_name' in request.GET and request.GET['user_name']:
            users = users.filter(user_name__icontains=request.GET['user_name'])
        if 'pan_no' in request.GET and request.GET['pan_no']:
            users = users.filter(pan_no__icontains=request.GET['pan_no'])
        if 'email' in request.GET and request.GET['email']:
            users = users.filter(email__icontains=request.GET['email'])
        if 'phone' in request.GET and request.GET['phone']:
            users = users.filter(phone__icontains=request.GET['phone'])

        # Apply sorting
        if sorting == "name_a_z":
            users = users.order_by("first_name")
        elif sorting == "name_z_a":
            users = users.order_by("-first_name")
        elif sorting == "recently_activated":
            users = users.filter(activation_status='1').order_by("-updated_at")
        elif sorting == "recently_deactivated":
            users = users.filter(
                Q(activation_status='0') | Q(activation_status__isnull=True) | Q(activation_status='')
            ).order_by("-updated_at")
        else:
            users = users.order_by("-updated_at")

        total_agents = Users.objects.filter(role_id__in=role_ids).count()
        active_agents = Users.objects.filter(role_id__in=role_ids, activation_status='1').count()
        
        deactive_agents = Users.objects.filter(role_id__in=role_ids).exclude(activation_status='1').count()
        pending_agents = 0  # Define pending logic if needed

        # Paginate results
        paginator = Paginator(users, per_page)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        counters = partnerCounters()

        return render(request, 'members/members-intraining.html', {
            'page_obj': page_obj,
            'total_agents': total_agents,
            'active_agents': active_agents,
            'counters': counters,
            'deactive_agents': deactive_agents,
            'pending_agents': pending_agents,
            'search_field': search_field,
            'search_query': search_query,
            'global_search': global_search,
            'sorting': sorting,
            'per_page': per_page,
        })
    else:
        return redirect('login')

    
    
# def members_inexam(request):
#     if request.user.is_authenticated:
#   
#             # Define the list of role IDs to filter
#             # role_ids = [2, 3, 4]
#             role_ids = [4]
#             # Filter users whose role_id is in the specified list
#             users = Users.objects.filter(role_id__in=role_ids)
#         else:
#             users = Users.objects.none()  # Return an empty queryset for unauthorized users
#         counters = partnerCounters()

#         partners = Partner.objects.filter(partner_status='3')
#         partner_ids = partners.values_list('user_id', flat=True)  # Get user IDs

#         users = Users.objects.filter(id__in=partner_ids)
#         return render(request, 'members/members-inexam.html', {
#             'counters': counters,
#             'users': users
#             })
#     else:
#         return redirect('login')

def members_inexam(request):
    if not request.user.is_authenticated:
        return redirect('login')

    
    user = request.user

    if user.role_id == 1 or str(user.department_id) in ["1","2"]:  # Admin role ID
        # Define role IDs for the user filter
        role_ids = [4]
        
        # Define pagination and search variables
        per_page = request.GET.get('per_page', 10)
        search_field = request.GET.get('search_field', '')
        search_query = request.GET.get('search_query', '')
        sorting = request.GET.get('sorting', '')
        global_search = request.GET.get('global_search', '').strip()
        
        try:
            per_page = int(per_page)
        except ValueError:
            per_page = 10  # Default to 10 if invalid value is given

        # Fetch users that are in the "in exam" stage (partner_status='3')
        partners = Partner.objects.filter(Q(partner_status='3')).exclude(active=0)
        partner_ids = partners.values_list('user_id', flat=True)  # Get user IDs

        users = Users.objects.filter(id__in=partner_ids, role_id__in=role_ids)

        # inexam = True  # Example condition to check if the user is in an exam
        # examresult = ExamResult.objects.filter(user_id__in=users.values_list('id', flat=True))  # Assu
        examresult_qs = ExamResult.objects.filter(user_id__in=users.values_list('id', flat=True))
        examresult_map = {result.user_id: result for result in examresult_qs}

        # Global search filtering
        if global_search:
            users = users.annotate(
                search_full_name=Concat('first_name', Value(' '), 'last_name')
            ).filter(
                Q(search_full_name__icontains=global_search) |  
                Q(first_name__icontains=global_search) |
                Q(last_name__icontains=global_search) |
                Q(email__icontains=global_search) |
                Q(phone__icontains=global_search)
            )

        # # Apply additional filtering based on specific fields
        # if search_field and search_query:
        #     filter_args = {f"{search_field}__icontains": search_query}
        #     users = users.filter(**filter_args)

         # Apply filtering
        if 'user_gen_id' in request.GET and request.GET['user_gen_id']:
            users = users.filter(user_gen_id__icontains=request.GET['user_gen_id'])
        if 'user_name' in request.GET and request.GET['user_name']:
            users = users.filter(user_name__icontains=request.GET['user_name'])
        if 'pan_no' in request.GET and request.GET['pan_no']:
            users = users.filter(pan_no__icontains=request.GET['pan_no'])
        if 'email' in request.GET and request.GET['email']:
            users = users.filter(email__icontains=request.GET['email'])
        if 'phone' in request.GET and request.GET['phone']:
            users = users.filter(phone__icontains=request.GET['phone'])

        # Sorting logic
        if sorting == "name_a_z":
            users = users.order_by("first_name")
        elif sorting == "name_z_a":
            users = users.order_by("-first_name")
        elif sorting == "recently_activated":
            users = users.filter(activation_status='1').order_by("-updated_at")
        elif sorting == "recently_deactivated":
            users = users.filter(
                Q(activation_status='0') | Q(activation_status__isnull=True) | Q(activation_status='')
            ).order_by("-updated_at")
        else:
            users = users.order_by("-updated_at")

        # Get totals for various status counts
        total_agents = Users.objects.filter(role_id__in=role_ids).count()
        active_agents = Users.objects.filter(role_id__in=role_ids, activation_status='1').count()
        deactive_agents = Users.objects.filter(role_id__in=role_ids).exclude(activation_status='1').count()

        # Paginate results
        paginator = Paginator(users, per_page)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        counters = partnerCounters()

        return render(request, 'members/members-inexam.html', {
            'page_obj': page_obj,
            'total_agents': total_agents,
            'active_agents': active_agents,
            'deactive_agents': deactive_agents,
            'counters': counters,
            'user': users,
            # 'inexam': inexam,
            'examresult': examresult_map,  # pass all results
            'search_field': search_field,
            'search_query': search_query,
            'global_search': global_search,
            'sorting': sorting,
            'per_page': per_page,
        })
    else:
        return redirect('login')

    
    
# def members_activated(request):
#     if request.user.is_authenticated:
#       
#             # Define the list of role IDs to filter
#             # role_ids = [2, 3, 4]
#             role_ids = [4]
#             # Filter users whose role_id is in the specified list
#             users = Users.objects.filter(role_id__in=role_ids)
#         else:
#             users = Users.objects.none()  # Return an empty queryset for unauthorized users
#         return render(request, 'members/members-activated.html', {'users': users})
#     else:
#         return redirect('login')
    
def members_activated(request):
    if not request.user.is_authenticated:
        return redirect('login')

    
    user = request.user

    if user.role_id == 1 or str(user.department_id) in ["1","2"]:
        role_ids = [4]  # Filter for specific roles

        per_page = request.GET.get('per_page', 10)
        search_field = request.GET.get('search_field', '')  # Field to search
        search_query = request.GET.get('search_query', '')  # Search value
        sorting = request.GET.get('sorting', '')  # Sorting option
        global_search = request.GET.get('global_search', '').strip()
        
        try:
            per_page = int(per_page)
        except ValueError:
            per_page = 10  # Default to 10 if invalid value is given

        # Base QuerySet
        
        role_id = request.user.role_id
        department_id = request.user.department_id
        user_id = request.user.id

        partners = Partner.objects.filter(partner_status='4').exclude(active=0)
        partner_ids = partners.values_list('user_id', flat=True)  # Get user IDs
        
        users = Users.objects.filter(id__in=partner_ids, activation_status=1)
        
        if role_id == 2:  # Management
            users = users

        elif role_id == 3:  # Branch Manager
            managers = Users.objects.filter(role_id=5, senior_id=user_id)
            team_leaders = Users.objects.filter(role_id=6, senior_id__in=managers.values_list('id', flat=True))
            relationship_managers = Users.objects.filter(role_id=7, senior_id__in=team_leaders.values_list('id', flat=True))

            user_ids = list(managers.values_list('id', flat=True)) + \
                    list(team_leaders.values_list('id', flat=True)) + \
                    list(relationship_managers.values_list('id', flat=True))
            users = users.filter(senior_id__in=user_ids)

        elif role_id == 4:  # Agent
            users = users.filter(senior_id=user_id)  # Agent can only see themselves

        elif str(department_id) == '1' and role_id == 5:  # Manager
            team_leaders = Users.objects.filter(role_id=6, senior_id=user_id)
            relationship_managers = Users.objects.filter(role_id=7, senior_id__in=team_leaders.values_list('id', flat=True))

            user_ids = list(team_leaders.values_list('id', flat=True)) + \
                    list(relationship_managers.values_list('id', flat=True)) 
            users = users.filter(senior_id__in=user_ids)

        elif str(department_id) == '1' and role_id == 6:  # Team Leader
            relationship_managers = Users.objects.filter(role_id=7, senior_id=user_id)
            user_ids = list(relationship_managers.values_list('id', flat=True))
            users = users.filter(senior_id__in=user_ids)

        elif str(department_id) == '1' and role_id == 7:  # Relationship Manager
            users = users.filter(senior_id=user_id)

        else:
            users = users

        
        if global_search:
            users = users.annotate(
                search_full_name=Concat('first_name', Value(' '), 'last_name')
            ).filter(
                Q(search_full_name__icontains=global_search) |  
                Q(first_name__icontains=global_search) |
                Q(last_name__icontains=global_search) |
                Q(email__icontains=global_search) |
                Q(phone__icontains=global_search)  
            )

        '''Apply filtering
        if search_field and search_query:
           filter_args = {f"{search_field}__icontains": search_query}
           users = users.filter(**filter_args)'''

        ## Apply filtering on specific fields ## ---parth
        if 'user_gen_id' in request.GET and request.GET['user_gen_id']:
            users =users.filter(user_gen_id__icontains=request.GET['user_gen_id'])
        if 'user_name' in request.GET and request.GET['user_name']:
            users =users.filter(user_name__icontains=request.GET['user_name'])
        if 'pan_no' in request.GET and request.GET['pan_no']:
            users =users.filter(pan_no__icontains=request.GET['pan_no'])
        if 'email' in request.GET and request.GET['email']:
            users = users.filter(email__icontains=request.GET['email']) 
        if 'phone' in request.GET and request.GET['phone']:
            users = users.filter(phone__icontains=request.GET['phone'])

        # Apply sorting
        if sorting == "name_a_z":
            users = users.order_by("first_name")
        elif sorting == "name_z_a":
            users = users.order_by("-first_name")
        elif sorting == "recently_activated":
            users = users.filter(activation_status='1').order_by("-updated_at")
        elif sorting == "recently_deactivated":
            users = users.filter(
                Q(activation_status='0') | Q(activation_status__isnull=True) | Q(activation_status='')
            ).order_by("-updated_at")
        else:
            users = users.order_by("-updated_at")

        total_agents = users.filter(role_id__in=role_ids).count()
        active_agents = users.filter(role_id__in=role_ids,activation_status='1').count()
        
        deactive_agents = users.filter(
            role_id__in=role_ids
        ).exclude(
            activation_status='1'
        ).count()
        pending_agents = 0  # Define pending logic if needed

        # Paginate results
        paginator = Paginator(users, per_page)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        counters = partnerCounters()
        
        return render(request, 'members/members-activated.html', {
            'page_obj': page_obj,
            'total_agents': total_agents,
            'active_agents': active_agents,
            'counters': counters,
            'deactive_agents': deactive_agents,
            'pending_agents': pending_agents,
            'search_field': search_field,
            'search_query': search_query,
            'global_search': global_search,
            'sorting': sorting,
            'per_page': per_page,
        })
    else:
        return redirect('login')
    

def members_rejected(request):
    if not request.user.is_authenticated:
        return redirect('login')
    
    user = request.user

    if user.role_id == 1 or str(user.department_id) in ["1","2"]:
        role_ids = [4]  # Filter for specific roles

        per_page = request.GET.get('per_page', 10)
        search_field = request.GET.get('search_field', '')  # Field to search
        search_query = request.GET.get('search_query', '')  # Search value
        sorting = request.GET.get('sorting', '')  # Sorting option
        global_search = request.GET.get('global_search', '').strip()
        
        try:
            per_page = int(per_page)
        except ValueError:
            per_page = 10  # Default to 10 if invalid value is given

        # Base QuerySet
        users = Users.objects.filter(role_id__in=role_ids, activation_status=5)

        partners = Partner.objects.filter(partner_status='6')
        partner_ids = partners.values_list('user_id', flat=True)  # Get user IDs

        users = Users.objects.filter(id__in=partner_ids)
        
        if global_search:
            users = users.annotate(
                search_full_name=Concat('first_name', Value(' '), 'last_name')
            ).filter(
                Q(search_full_name__icontains=global_search) |  
                Q(first_name__icontains=global_search) |
                Q(last_name__icontains=global_search) |
                Q(email__icontains=global_search) |
                Q(phone__icontains=global_search)  
            )

        # # Apply filtering
        # if search_field and search_query:
        #     filter_args = {f"{search_field}__icontains": search_query}
        #     users = users.filter(**filter_args)

         # Apply filtering
        if 'user_gen_id' in request.GET and request.GET['user_gen_id']:
            users = users.filter(user_gen_id__icontains=request.GET['user_gen_id'])
        if 'user_name' in request.GET and request.GET['user_name']:
            users = users.filter(user_name__icontains=request.GET['user_name'])
        if 'pan_no' in request.GET and request.GET['pan_no']:
            users = users.filter(pan_no__icontains=request.GET['pan_no'])
        if 'email' in request.GET and request.GET['email']:
            users = users.filter(email__icontains=request.GET['email'])
        if 'phone' in request.GET and request.GET['phone']:
            users = users.filter(phone__icontains=request.GET['phone'])


        # Apply sorting
        if sorting == "name_a_z":
            users = users.order_by("first_name")
        elif sorting == "name_z_a":
            users = users.order_by("-first_name")
        elif sorting == "recently_activated":
            users = users.filter(activation_status='1').order_by("-updated_at")
        elif sorting == "recently_deactivated":
            users = users.filter(
                Q(activation_status='0') | Q(activation_status__isnull=True) | Q(activation_status='')
            ).order_by("-updated_at")
        else:
            users = users.order_by("-updated_at")

        
        total_agents = Users.objects.filter(role_id__in=role_ids).count()
        active_agents = Users.objects.filter(role_id__in=role_ids,activation_status='1').count()
        
        deactive_agents = Users.objects.filter(
            role_id__in=role_ids
        ).exclude(
            activation_status='1'
        ).count()
        pending_agents = 0  # Define pending logic if needed

        # Paginate results
        paginator = Paginator(users, per_page)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        counters = partnerCounters()

        return render(request, 'members/members-rejected.html', {
            'page_obj': page_obj,
            'total_agents': total_agents,
            'active_agents': active_agents,
            'deactive_agents': deactive_agents,
            'counters': counters,
            'pending_agents': pending_agents,
            'search_field': search_field,
            'search_query': search_query,
            'global_search': global_search,
            'sorting': sorting,
            'per_page': per_page,
        })
    else:
        return redirect('login')

def members_inactive(request):
    if not request.user.is_authenticated:
        return redirect('login')

    
    user = request.user

    if user.role_id == 1 or str(user.department_id) in ["1","2"]:
        role_ids = [4]  # Filter for specific roles

        per_page = request.GET.get('per_page', 10)
        search_field = request.GET.get('search_field', '')  # Field to search
        search_query = request.GET.get('search_query', '')  # Search value
        sorting = request.GET.get('sorting', '')  # Sorting option
        global_search = request.GET.get('global_search', '').strip()

        try:
            per_page = int(per_page)
        except ValueError:
            per_page = 10  # Default to 10 if invalid value is given

        # Base QuerySet
        users = Users.objects.filter(role_id__in=role_ids, activation_status='0')  # Inactive users

        # Get partners with 'Inactive' status
        partners = Partner.objects.filter(partner_status='5')  # Inactive partners
        partner_ids = partners.values_list('user_id', flat=True)  # Get user IDs

        users = Users.objects.filter(id__in=partner_ids)

        if global_search:
            users = users.annotate(
                search_full_name=Concat('first_name', Value(' '), 'last_name')
            ).filter(
                Q(search_full_name__icontains=global_search) |  
                Q(first_name__icontains=global_search) |
                Q(last_name__icontains=global_search) |
                Q(email__icontains=global_search) |
                Q(phone__icontains=global_search)
            )

        # Apply filtering
        if 'user_gen_id' in request.GET and request.GET['user_gen_id']:
            users = users.filter(user_gen_id__icontains=request.GET['user_gen_id'])
        if 'user_name' in request.GET and request.GET['user_name']:
            users = users.filter(user_name__icontains=request.GET['user_name'])
        if 'pan_no' in request.GET and request.GET['pan_no']:
            users = users.filter(pan_no__icontains=request.GET['pan_no'])
        if 'email' in request.GET and request.GET['email']:
            users = users.filter(email__icontains=request.GET['email'])
        if 'phone' in request.GET and request.GET['phone']:
            users = users.filter(phone__icontains=request.GET['phone'])

        # Apply sorting
        if sorting == "name_a_z":
            users = users.order_by("first_name")
        elif sorting == "name_z_a":
            users = users.order_by("-first_name")
        elif sorting == "recently_activated":
            users = users.filter(activation_status='1').order_by("-updated_at")
        elif sorting == "recently_deactivated":
            users = users.filter(
                Q(activation_status='0') | Q(activation_status__isnull=True) | Q(activation_status='')
            ).order_by("-updated_at")
        else:
            users = users.order_by("-updated_at")

        total_agents = Users.objects.filter(role_id__in=role_ids).count()
        active_agents = Users.objects.filter(role_id__in=role_ids, activation_status='1').count()
        deactive_agents = Users.objects.filter(role_id__in=role_ids, activation_status='0').count()

        # Paginate results
        paginator = Paginator(users, per_page)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        counters = partnerCounters()

        return render(request, 'members/members-inactive.html', {
            'page_obj': page_obj,
            'total_agents': total_agents,
            'active_agents': active_agents,
            'counters': counters,
            'deactive_agents': deactive_agents,
            'pending_agents': 0,  # Define pending logic if needed
            'search_field': search_field,
            'search_query': search_query,
            'global_search': global_search,
            'sorting': sorting,
            'per_page': per_page,
        })
    else:
        return redirect('login')

    
def memberView(request, user_id):
    if request.user.is_authenticated:
        # Fetch user details and bank details
        user_details  = Users.objects.get(id=user_id)
        bank_details  = BankDetails.objects.filter(user_id=user_id).first()
        partner_info  = Partner.objects.filter(user_id=user_id).first()
    
        update_exam_eligible_status()

        if not partner_info: 
            sync_user_to_partner(user_id, request)
            partner_info  = Partner.objects.filter(user_id=user_id).first()

        # 2) Advance through training/exam windows
        #    - Activated→In‑Training
        #    - In‑Training→In‑Exam after 5 days
        #    - In‑Exam→Activated after 7 more days
        # if partner_info:
        #    partner_info.start_training_and_exam()

        # bqp_details = BqpMaster.objects.filter(id=user_details.bqp_id).first()
        bqp_details  = BqpMaster.objects.all()

        # Exam Result
        examresult = ExamResult.objects.filter(user=request.user).first()
        inexam =True if examresult else False  


        # if in partner table user_id not exist only then hit this 

        docs = DocumentUpload.objects.filter(user_id=user_id).first()
        # Fetch commissions for the specific member
        query = """
            SELECT c.*, u.first_name, u.last_name, c.product_id
            FROM commissions c
            INNER JOIN users u ON c.member_id = u.id
            WHERE c.member_id = %s
        """
        
        with connection.cursor() as cursor:
            cursor.execute(query, [user_id])
            commissions_list = dictfetchall(cursor)

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

        branches = Branch.objects.filter(status='Active').order_by('-created_at')

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

        
        selected_branch_id = branch.id if branch else None
        selected_manager_id = manager.id if manager else None
        selected_tl_id = tl.id if tl else None
        selected_rm_id = rm.id if rm else None

        print('hello')
        # print(bqp_details.id)
        print('hello')
        return render(request, 'members/member-view.html', {
            'user_details': user_details,
            'bank_details': bank_details,
            'partner_status': partner_info.partner_status,
            'docs': docs,
            'manager_list': manager_list,
            'rm_list': rm_list,
            'tl_list': tl_list,
            'branches': branches,
            'bqp_details' : bqp_details,
            'inexam': inexam,
            'examresult': examresult , # Pass the exam result to the template
            'rm_details': rm,
            'tl_details': tl,
            'branch': branch,
            'manager_details': manager,
            'commissions': commissions_list, 
            'products': products,  
            'selected_branch_id': selected_branch_id,
            'selected_manager_id': selected_manager_id,
            'selected_tl_id': selected_tl_id,
            'selected_rm_id': selected_rm_id,
        })
    else:
        return redirect('login')
    
    
def get_branch_managers(request):
    branch_id = request.GET.get('branch_id')
    branch_managers = Users.objects.filter(branch_id=branch_id, department_id=1, role_id=5).values('id', 'first_name', 'last_name')
    managers_list = [{'id': manager['id'], 'full_name': f"{manager['first_name']} {manager['last_name']}"} for manager in branch_managers]
    return JsonResponse({'branch_managers': managers_list})

def get_sales_managers(request):
    branch_manager_id = request.GET.get('branch_manager_id')
    sales_managers = Users.objects.filter(senior_id=branch_manager_id, role_id=6).values('id', 'first_name', 'last_name')
    sales_list = [{'id': manager['id'], 'full_name': f"{manager['first_name']} {manager['last_name']}"} for manager in sales_managers]
    return JsonResponse({'sales_managers': sales_list})


def get_rm_list(request):
    tlId = request.GET.get('tlId')
    sales_managers = Users.objects.filter(senior_id=tlId, role_id=7).values('id', 'first_name', 'last_name')
    rm_list = [{'id': manager['id'], 'full_name': f"{manager['first_name']} {manager['last_name']}"} for manager in sales_managers]
    return JsonResponse({'rm_list': rm_list})

# LATEST CODE  
from django.templatetags.static import static  # ✅ Import static

def activationPdf(request, user_id):
    """Generate a PDF for the user and return the file path."""
    wkhtml_path = os.getenv('WKHTML_PATH', getattr(settings, 'WKHTML_PATH', r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'))
    config = pdfkit.configuration(wkhtmltopdf=wkhtml_path)

    customer = get_object_or_404(Users, id=user_id)

    training_pdf_path = os.path.join(settings.MEDIA_ROOT, 'training/Training_Material_Elevate_Insurance_V1.0.pdf')

    context = {
        "user": customer,
        "support_email": getattr(settings, 'SUPPORT_EMAIL', 'support@elevateinsurance.in'),
        "company_website": getattr(settings, 'COMPANY_WEBSITE', 'https://pos.elevateinsurance.in/'),
        "sub_broker_test_url": getattr(settings, 'SUB_BROKER_TEST_URL', 'https://pos.elevateinsurance.in/'),
        "terms_conditions_url": getattr(settings, 'TERMS_URL', 'https://pos.elevateinsurance.in/empPortal/media/terms/Terms_And_Conditions.pdf'),
        "training_material_url": training_pdf_path,
        "support_number": getattr(settings, 'SUPPORT_NUMBER', '+918887779999'),
        "logo_url": request.build_absolute_uri(static('dist/img/logo2.png')),
    }

    html_content = render_to_string("members/activation-pdf.html", context)

    options = {
        'enable-local-file-access': '',
        'page-size': 'A4',
        'encoding': "UTF-8",
    }

    pdf_path = os.path.join(settings.MEDIA_ROOT, f'account_activation_{user_id}.pdf')

    try:
        pdfkit.from_string(html_content, pdf_path, configuration=config, options=options)
        return pdf_path
    except Exception as e:
        logger.error(f"PDF generation failed for user {user_id}: {e}")
        return None




def activateUser(request, user_id):
    if not request.user.is_authenticated:
        return redirect('login')

    docs = DocumentUpload.objects.filter(user_id=user_id).first()

    if docs and all([
        docs.aadhaar_card_front_status == 'Approved',
        docs.aadhaar_card_back_status == 'Approved',
        docs.upload_pan_status == 'Approved',
        docs.upload_cheque_status == 'Approved',
        docs.tenth_marksheet_status == 'Approved'
    ]):
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE users SET user_active = %s, activation_status = %s WHERE id = %s",
                    ['1', '1', user_id]
                )

            user = get_object_or_404(Users, id=user_id)
            user_email = user.email

            training_file_name = getattr(settings, 'TRAINING_PDF_PATH', 'training/Training_Material_Elevate_Insurance_V1.0.pdf')
            training_pdf_path = os.path.join(settings.MEDIA_ROOT, training_file_name)
            training_material_url = request.build_absolute_uri(settings.MEDIA_URL + training_file_name)

            email_body = render_to_string('members/activation-email.html', {
                'user': user,
                'logo_url': request.build_absolute_uri(static(getattr(settings, 'GLOBAL_FILE_LOGO', 'dist/img/logo2.png'))),
                'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@elevateinsurance.in'),
                'terms_conditions_url': request.build_absolute_uri(settings.MEDIA_URL + 'terms/Terms_And_Conditions.pdf'),
                'company_website': getattr(settings, 'COMPANY_WEBSITE', 'https://pos.elevateinsurance.in/'),
                'sub_broker_test_url': getattr(settings, 'SUB_BROKER_TEST_URL', 'https://pos.elevateinsurance.in/'),
                'training_material_url': training_material_url,
                'support_number': getattr(settings, 'SUPPORT_PARTNER_PHONE', '+918887779999'),
            })

            subject = 'Account Activated Successfully'
            from_email = settings.DEFAULT_FROM_EMAIL
            recipient_list = [user_email]

            email = EmailMessage(subject, email_body, from_email, recipient_list)
            email.content_subtype = "html"

            if os.path.exists(training_pdf_path):
                email.attach_file(training_pdf_path)
            else:
                logger.error(f"Training PDF not found: {training_pdf_path}")

            email.send()
            messages.success(request, "User account has been activated successfully!")

        except Exception as e:
            logger.error(f"Error activating user: {e}")
            messages.error(request, "An error occurred during activation.")
    else:
        messages.error(request, "User cannot be activated. Please ensure all required documents are approved.")

    return redirect('member-view', user_id=user_id)


def updatePartnerStatus(request, user_id):
    partner_status = request.POST.get('partner_status')

    if partner_status is not None:
        try:
            partner_status = int(partner_status)  # Convert to int
        except ValueError:
            messages.error(request, "Invalid status selected.")
            return redirect('member-view', user_id=user_id)
        
     # Fetch user documents for approval check
        docs = DocumentUpload.objects.filter(user_id=user_id).first() 

        
        # Check if documents are approved before activating
        if partner_status == 4:  # Activated status
            if not docs or not all([
                docs.aadhaar_card_front_status == 'Approved',
                docs.aadhaar_card_back_status == 'Approved',
                docs.upload_pan_status == 'Approved',
                docs.upload_cheque_status == 'Approved',
                docs.tenth_marksheet_status == 'Approved'
            ]):
                messages.error(request, "User cannot be activated. Please ensure all required documents are approved.")
                return redirect('member-view', user_id=user_id)   

        update_successful = update_partner_by_user_id(
            user_id=user_id,
            update_fields={"partner_status": partner_status},
            request=request
        )
        if partner_status == 3:
            Users.objects.filter(id=user_id).update(exam_eligibility=1)

        #  If they just moved into “Activated” (4), go through your full activateUser flow
        if partner_status == 4:
        # activateUser will do its own messages.success / messages.error
            activate_response = activateUser(request, user_id)
            if activate_response:
                return activate_response
            
            
            # Then, run the login activation process
            login_activate_response = loginActivateUser(request, user_id)
            if login_activate_response:
                return login_activate_response 
            
         # If Inactive
        if partner_status == 5:
            deactivate_response = deactivateUser(request, user_id)
            if deactivate_response:
                return deactivate_response    

        if update_successful:
            messages.success(request, "Partner status updated successfully.")
        else:
            messages.warning(request, "No changes were made to the partner status.")


    return redirect('member-view', user_id=user_id)  

def deactivateUser(request, user_id):
    if not request.user.is_authenticated:
        return redirect('login')

    try:
        # Update user activation status in the database
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE users SET user_active = %s WHERE id = %s",
                ['0', user_id]
            )

        user = get_object_or_404(Users, id=user_id)
        user_email = user.email

        training_file_name = getattr(settings, 'TRAINING_PDF_PATH', 'training/Training_Material_Elevate_Insurance_V1.0.pdf')
        training_material_url = request.build_absolute_uri(settings.MEDIA_URL + training_file_name)

        # Render email HTML template
        email_body = render_to_string('members/activation-email.html', {
            'user': user,
            'logo_url': request.build_absolute_uri(static(getattr(settings, 'GLOBAL_FILE_LOGO', 'dist/img/logo2.png'))),
            'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@elevateinsurance.in'),
            'terms_conditions_url': request.build_absolute_uri(settings.MEDIA_URL + 'terms/Terms_And_Conditions.pdf'),
            'company_website': getattr(settings, 'COMPANY_WEBSITE', 'https://pos.elevateinsurance.in/'),
            'sub_broker_test_url': getattr(settings, 'SUB_BROKER_TEST_URL', 'https://pos.elevateinsurance.in/'),
            'training_material_url': training_material_url,
            'support_number': getattr(settings, 'SUPPORT_PARTNER_PHONE', '+918887779999'),
        })

        subject = 'Account Deactivated'
        from_email = settings.DEFAULT_FROM_EMAIL
        recipient_list = [user_email]

        email = EmailMessage(subject, email_body, from_email, recipient_list)
        email.content_subtype = "html"

        # Uncomment if email should be sent during deactivation
        # email.send()

        messages.success(request, "User account has been deactivated successfully!")

    except Exception as e:
        logger.error(f"Error deactivating user: {e}")
        messages.error(request, "An error occurred during deactivation.")

    return redirect('member-view', user_id=user_id)

def loginActivateUser(request, user_id):
    if not request.user.is_authenticated:
        return redirect('login')

    try:
        # Update user activation status in the database
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE users SET user_active = %s WHERE id = %s",
                ['1', user_id]
            )

        user = get_object_or_404(Users, id=user_id)
        user_email = user.email

        training_file_name = getattr(settings, 'TRAINING_PDF_PATH', 'training/Training_Material_Elevate_Insurance_V1.0.pdf')
        training_material_url = request.build_absolute_uri(settings.MEDIA_URL + training_file_name)

        # Render email HTML template
        email_body = render_to_string('members/activation-email.html', {
            'user': user,
            'logo_url': request.build_absolute_uri(static(getattr(settings, 'GLOBAL_FILE_LOGO', 'dist/img/logo2.png'))),
            'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@elevateinsurance.in'),
            'terms_conditions_url': request.build_absolute_uri(settings.MEDIA_URL + 'terms/Terms_And_Conditions.pdf'),
            'company_website': getattr(settings, 'COMPANY_WEBSITE', 'https://pos.elevateinsurance.in/'),
            'sub_broker_test_url': getattr(settings, 'SUB_BROKER_TEST_URL', 'https://pos.elevateinsurance.in/'),
            'training_material_url': training_material_url,
            'support_number': getattr(settings, 'SUPPORT_PARTNER_PHONE', '+918887779999'),
        })

        subject = 'Account Activated Successfully'
        from_email = settings.DEFAULT_FROM_EMAIL
        recipient_list = [user_email]

        email = EmailMessage(subject, email_body, from_email, recipient_list)
        email.content_subtype = "html"  # Set content type to HTML

        # Optional: Attach PDF if needed
        # pdf_path = activationPdf(request, user_id)
        # if pdf_path and os.path.exists(pdf_path):
        #     email.attach_file(pdf_path)

        # Optional: Send email
        # email.send()

        messages.success(request, "User account has been activated successfully!")

    except Exception as e:
        logger.error(f"Error activating user: {e}")
        messages.error(request, "An error occurred during activation.")

    return redirect('member-view', user_id=user_id)




# LATEST CODE

    

def dictfetchall(cursor):
    "Returns all rows from a cursor as a dict"
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

def myAccount(request):
    if request.user.is_authenticated:
        # Fetch user and bank details for the logged-in user
        user_details = Users.objects.get(id=request.user.id)  # Fetching the user's details
        bank_details = BankDetails.objects.filter(user_id=request.user.id).first()  # Fetching bank details

        return render(request, 'profile/my-account.html', {
            'user_details': user_details,
            'bank_details': bank_details
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

        messages.success(request, "User details updated successfully!")
        return redirect('my-account')  # Redirect back to the user profile page

def storeOrUpdateBankDetails(request):
    if request.method == "POST":
        user_id = request.user.id  # Get the logged-in user's ID
        
        # Check if the bank details already exist for this user
        bank_details, created = BankDetails.objects.get_or_create(user_id=user_id)
        
        # Update the bank details
        bank_details.account_holder_name = request.POST.get('account_holder_name')
        bank_details.re_enter_account_number = request.POST.get('re_enter_account_number')
        bank_details.account_number = request.POST.get('account_number')
        bank_details.ifsc_code = request.POST.get('ifsc_code')
        bank_details.city = request.POST.get('city')
        bank_details.state = request.POST.get('state')
        
        # Save the updated or newly created bank details
        bank_details.save()

        # Show success message
        messages.success(request, "Bank details have been updated successfully.")
        
        # Redirect to the my-account page after saving the details
        return redirect('my-account')

    # If not a POST request, redirect to my-account
    return redirect('my-account')



def update_doc_status(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON data"}, status=400)

        doc_type = data.get("docType")
        status = data.get("status")
        doc_id = data.get("docId")
        reject_note = data.get("rejectNote", "")

        if not doc_type or not status or not doc_id:
            return JsonResponse({"error": "Missing required parameters"}, status=400)

        valid_statuses = ["Pending", "Approved", "Rejected"]
        if status not in valid_statuses:
            return JsonResponse({"error": "Invalid status"}, status=400)

        document = get_object_or_404(DocumentUpload, id=doc_id)
        user_id = document.user_id
        status_field = f"{doc_type}_status"
        updated_at_field = f"{doc_type}_updated_at"
        reject_note_field = f"{doc_type}_reject_note"

        if not hasattr(document, status_field) or not hasattr(document, updated_at_field):
            return JsonResponse({"error": "Invalid document type"}, status=400)

        setattr(document, status_field, status)
        setattr(document, updated_at_field, now())

        # Store rejection note if status is Rejected
        if status == "Rejected" and hasattr(document, reject_note_field):
            setattr(document, reject_note_field, reject_note)

        document.save()

        docs = DocumentUpload.objects.filter(user_id=user_id)
        if docs.exists():
            all_approved = all(doc.aadhaar_card_front_status == 'Approved' and
                               doc.aadhaar_card_back_status == 'Approved' and
                               doc.upload_pan_status == 'Approved' and
                               doc.upload_cheque_status == 'Approved' and
                               doc.tenth_marksheet_status == 'Approved' for doc in docs)
            any_pending = any(doc.aadhaar_card_front_status == 'Pending' or
                              doc.aadhaar_card_back_status == 'Pending' or
                              doc.upload_pan_status == 'Pending' or
                              doc.upload_cheque_status == 'Pending' or
                              doc.tenth_marksheet_status == 'Pending' for doc in docs)
            if all_approved:
                doc_status = '3'  # All documents approved
            elif any_pending:
                doc_status = '2'  # At least one document pending
            else:
                doc_status = '1'  # Some documents rejected or other statuses
            # Update partner status based on document statuses
            update_partner_by_user_id(user_id, {"doc_status": doc_status}, request=request)

            if all_approved: 
                update_partner_by_user_id(
                    user_id,
                    {
                        "partner_status": "2",
                        "training_started_at": localtime().replace(microsecond=0, tzinfo=None),
                    },
                    request=request
                )
                send_training_mail(request,user_id)
        if document.user_id:
            updateUserStatus(doc_id, document.user_id)
        return JsonResponse({"success": True, "message": f"Status updated to {status}!"})

    return JsonResponse({"error": "Invalid request method"}, status=405)



def deleteMember(request, user_id):
    if not request.user.is_authenticated:
        return redirect('login')

    update_partner_by_user_id(user_id, {"active": 0}, request=request)

    messages.success(request, "Memeber Deleted successfully!")
    return redirect(request.META.get('HTTP_REFERER', 'members'))

 
def requestForDoc(request, user_id):
    if not request.user.is_authenticated:
        return redirect('login')

    user = get_object_or_404(Users, id=user_id)
    partner = get_object_or_404(Partner, user_id=user_id)

    try:
        if user and user.email:
            email_body = render_to_string('members/request-doc-email.html', {
                'user': user,
                'logo_url': request.build_absolute_uri(static(getattr(settings, 'GLOBAL_FILE_LOGO', 'dist/img/logo2.png'))),
                'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@elevateinsurance.in'),
                'company_website': getattr(settings, 'COMPANY_WEBSITE', 'https://pos.elevateinsurance.in/'),
                'support_number': getattr(settings, 'SUPPORT_PARTNER_PHONE', '+918887779999'),
            })

            subject = 'Action Required: Please Upload Your Documents'
            from_email = settings.DEFAULT_FROM_EMAIL
            recipient_list = [user.email]

            email = EmailMessage(subject, email_body, from_email, recipient_list)
            email.content_subtype = "html"
            email.send()

    except Exception as e:
        logger.error(f"Error requesting document for user {user_id}: {e}")

    messages.success(request, "Request sent successfully!")
    return redirect(request.META.get('HTTP_REFERER', 'members'))



def send_training_mail(request, user_id):
    if not request.user.is_authenticated:
        return redirect('login')

    try:
        user = get_object_or_404(Users, id=user_id)
        user_email = user.email

        training_filename = getattr(settings, 'TRAINING_MATERIAL_FILE', 'training/Training_Material_Elevate_Insurance_V1.0.pdf')
        training_pdf_path = os.path.join(settings.MEDIA_ROOT, training_filename)
        training_material_url = request.build_absolute_uri(settings.MEDIA_URL + training_filename)

        email_body = render_to_string('members/training-email.html', {
            'user': user,
            'logo_url': request.build_absolute_uri(static(getattr(settings, 'GLOBAL_FILE_LOGO', 'dist/img/logo2.png'))),
            'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@elevateinsurance.in'),
            'terms_conditions_url': getattr(settings, 'TERMS_CONDITIONS_URL', 'https://pos.elevateinsurance.in/empPortal/media/terms/Terms_And_Conditions.pdf'),
            'company_website': getattr(settings, 'COMPANY_WEBSITE', 'https://pos.elevateinsurance.in/'),
            'training_material_url': training_material_url,
            'support_number': getattr(settings, 'SUPPORT_PARTNER_PHONE', '+918887779999'),
        })

        subject = 'Training Material for Your Account'
        from_email = settings.DEFAULT_FROM_EMAIL
        recipient_list = [user_email]

        email = EmailMessage(subject, email_body, from_email, recipient_list)
        email.content_subtype = "html"

        if os.path.exists(training_pdf_path):
            email.attach_file(training_pdf_path)
        else:
            logger.error(f"Training PDF not found: {training_pdf_path}")

        email.send()
        logger.info(f"Training email sent to {user_email} successfully.")

    except Exception as e:
        logger.error(f"Error sending training email to user {user_id}: {e}")


def updateUserStatus(doc_id, user_id):
    document = get_object_or_404(DocumentUpload, id=doc_id)
    user = get_object_or_404(Users, id=user_id)

    statuses = [
        document.aadhaar_card_front_status,
        document.aadhaar_card_back_status,
        document.upload_pan_status,
        document.upload_cheque_status,
        document.tenth_marksheet_status
    ]

    if any(status == 'Approved' for status in statuses) and all(status != 'Rejected' for status in statuses):
        user.activation_status = 4  # At least one approved, none rejected
        user.save()
    elif any(status == 'Rejected' for status in statuses):
        user.activation_status = 5  # At least one rejected
        user.save()

def add_partner(request):
    
    if not request.user.is_authenticated:
        return redirect('login')
    
    if request.method == 'POST':
        # Extract form data
        full_name = request.POST.get('full_name', '').strip()
        gender = request.POST.get('gender', '').strip()
        email = request.POST.get('email', '').strip()
        mobile = request.POST.get('mobile', '').strip()
        password = request.POST.get('password', '').strip()
        dob = request.POST.get('dob', '').strip()
        pan_no = request.POST.get('pan_no', '').strip().upper()

        # Splitting full name into first and last name
        name_parts = full_name.split()
        first_name = name_parts[0] if name_parts else ''
        last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ''

        # Use a dictionary for field-specific errors
        errors = {}

        if not full_name:
            errors['full_name'] = 'Full Name is required.'
        if not gender:
            errors['gender'] = 'Gender is required.'
        if not email:
            errors['email'] = 'Email Address is required.'
        elif not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
            errors['email'] = 'Invalid email format.'
        elif Users.objects.filter(email=email).exists():
            errors['email'] = 'This email is already registered.'
        if not mobile:
            errors['mobile'] = 'Mobile Number is required.'
        if not mobile.isdigit():
            errors['mobile'] = 'Mobile number must contain only digits.'
        elif len(mobile) != 10:
            errors['mobile'] = 'Mobile number must be 10 digits long.'
        elif mobile[0] not in '6789':
            errors['mobile'] = 'Mobile number must start with 6, 7, 8, or 9.'
        elif Users.objects.filter(phone=mobile).exists():
            errors['mobile'] = 'This mobile number is already registered.'
        if not password:
            errors['password'] = 'Password is required.'
        elif len(password) < 6:
            errors['password'] = 'Password must be at least 6 characters long.'
        if not dob:
            errors['dob'] = 'Date of Birth is required.'
        else:
            try:
                dob_date = datetime.datetime.strptime(dob, '%Y-%m-%d').date()
                today = datetime.date.today()

                if dob_date >= today:
                    errors['dob'] = 'Date of Birth must be in the past.'
                else:
                    age = (today - dob_date).days // 365
                    if age < 18:
                        errors['dob'] = 'You must be at least 18 years old.'
            except ValueError:
                errors['dob'] = 'Invalid date format. Use YYYY-MM-DD.'

        if not pan_no:
            errors['pan_no'] = 'PAN Number is required.'
        elif not re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]$', pan_no):
            errors['pan_no'] = 'Invalid PAN number format. Format should be ABCDE1234F.'
        elif Users.objects.filter(pan_no=pan_no).exists():
            errors['pan_no'] = 'This PAN number is already registered.'

        # If there are errors, re-render the form with field values and errors.
        if errors:
            return render(request, 'members/add_partner.html', {
                'full_name': full_name,
                'gender': gender,
                'email': email,
                'mobile': mobile,
                'dob': dob,
                'pan_no': pan_no,
                'errors': errors,
            })

        # Generate User ID
        last_user = Users.objects.all().order_by('-id').first()
        if last_user and last_user.user_gen_id.startswith('UR-'):
            last_user_gen_id = int(last_user.user_gen_id.split('-')[1])
            new_gen_id = f"UR-{last_user_gen_id + 1:04d}"
        else:
            new_gen_id = "UR-0001"

        # Hash password
        hashed_password = make_password(password)

        # Create new user
        user = Users(
            user_gen_id=new_gen_id,
            role_id=4,  # Assuming role is assigned later
            role_name="User",
            user_name=full_name,
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=mobile,
            gender=gender,
            password=hashed_password,
            dob=dob,
            pan_no=pan_no,
            status=1,
            is_active=1
        )
        user.save()

        
        # sync_user_to_partner(user.id, request) 

        messages.success(request, "Partner added successfully!")
        return redirect('members')  # Redirect to a desired page

    return render(request, 'members/add_partner.html')

logger = logging.getLogger(__name__)

"""def upload_excel_users(request):
    if request.method == "POST" and request.FILES.get("excel_file"):
        excel_file = request.FILES["excel_file"]
        ext = os.path.splitext(excel_file.name)[1]

        if ext.lower() not in [".xlsx", ".xls"]:
            messages.error(request, "Only Excel files (.xlsx, .xls) are allowed!")
            return redirect("upload-partners-excel")

        try:
            wb = openpyxl.load_workbook(excel_file)
            sheet = wb.active

            inserted = 0
            duplicate_data_found = False

            for row in sheet.iter_rows(min_row=2, values_only=True):
                full_name, gender_str, email, mobile, password, dob, pan_no = [str(cell).strip() if cell else '' for cell in row]

                # ---------- VALIDATION ----------
                if not full_name:
                    logger.warning(f"Skipped: Missing full name - Row: {row}")
                    continue

                name_parts = full_name.split()
                first_name = name_parts[0]
                last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

                if gender_str.lower() not in ['male', 'female']:
                    logger.warning(f"Skipped: Invalid gender - {gender_str}")
                    continue
                gender = 1 if gender_str.lower() == "male" else 2

                if not email or not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
                    logger.warning(f"Skipped: Invalid email - {email}")
                    continue

                if not mobile or not mobile.isdigit() or len(mobile) != 10 or mobile[0] not in "6789":
                    logger.warning(f"Skipped: Invalid mobile - {mobile}")
                    continue

                if not password or len(password) < 6:
                    logger.warning(f"Skipped: Password too short - {full_name}")
                    continue

                try:
                    dob_date = parser.parse(dob).date()
                    today = datetime.date.today()
                    age = (today - dob_date).days // 365
                    if dob_date >= today or age < 18:
                        logger.warning(f"Skipped: Invalid DOB or under 18 - {dob}")
                        continue
                except Exception as e:
                    logger.warning(f"Skipped: DOB parsing error - {dob}, Error: {e}")
                    continue

                if not pan_no or not re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]$', pan_no.upper()):
                    logger.warning(f"Skipped: Invalid PAN - {pan_no}")
                    continue

                # ---------- DUPLICATE CHECK ----------
                if Users.objects.filter(email=email).exists() or \
                   Users.objects.filter(phone=mobile).exists() or \
                   Users.objects.filter(pan_no=pan_no.upper()).exists():
                    logger.info(f"Duplicate Found: {email}, {mobile}, {pan_no}")
                    duplicate_data_found = True
                    continue

                # ---------- USER GEN ID ----------
                last_user = Users.objects.order_by("-id").first()
                if last_user and last_user.user_gen_id.startswith("UR-"):
                    last_id = int(last_user.user_gen_id.split("-")[1])
                    user_gen_id = f"UR-{last_id + 1:04d}"
                else:
                    user_gen_id = "UR-0001"

                # ---------- SAVE TO DATABASE ----------
                hashed_password = make_password(password)

                Users.objects.create(
                    user_gen_id=user_gen_id,
                    role_id=4,
                    role_name="User",
                    user_name=full_name,
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    phone=mobile,
                    gender=gender,
                    password=hashed_password,
                    dob=dob_date,
                    pan_no=pan_no.upper(),
                    status=1,
                    is_active=1
                )

                inserted += 1

            # ---------- FINAL MESSAGE ----------
            if inserted > 0:
                messages.success(request, f"{inserted} leads uploaded successfully.")
            elif duplicate_data_found:
                messages.warning(request, "No new leads were inserted. All records were duplicates.")
            else:
                messages.info(request, "No valid data found in Excel file!")

        except Exception as e:
            logger.error(f"Excel processing error: {e}")
            messages.error(request, f"Error processing file: {e}")
        return redirect("upload-partners-excel")

    return render(request, "members/upload_excel.html")"""
@login_required
def upload_excel_users(request):
    if request.method == "POST" and request.FILES.get("excel_file"):
        excel_file = request.FILES["excel_file"]

        if not excel_file.name.lower().endswith((".xlsx", ".xls")):
            messages.error(request, "Only Excel files (.xlsx, .xls) are allowed!")
            return redirect("upload-partners-excel")

        instance = PartnerUploadExcel.objects.create(
            file=excel_file,
            file_name=excel_file.name,
            file_url=excel_file.name,
            created_by=request.user,
        )

        # Trigger background task
        async_task("empPortal.taskz.process_partner_excel.process_partner_excel", instance.id)

        messages.success(request, "Excel uploaded. It will be processed shortly in background.")
        return redirect("upload-partners-excel")

    return render(request, "members/upload_excel.html")

def myTeamView(request):
    if not request.user.is_authenticated or request.user.is_active != 1:
        messages.error(request, 'Login First')
        return redirect('login')

    role_id = request.user.role_id
    user_id = request.user.id

    my_team = Users.objects.none()  # Default empty queryset

    if role_id == 2:  # Management
        my_team = Users.objects.all()

    elif role_id == 3:  # Branch Manager
        managers = Users.objects.filter(role_id=5, senior_id=user_id)
        team_leaders = Users.objects.filter(role_id=6, senior_id__in=managers.values_list('id', flat=True))
        relationship_managers = Users.objects.filter(role_id=7, senior_id__in=team_leaders.values_list('id', flat=True))

        user_ids = list(managers.values_list('id', flat=True)) + \
                   list(team_leaders.values_list('id', flat=True)) + \
                   list(relationship_managers.values_list('id', flat=True))
        my_team = Users.objects.filter(id__in=user_ids)

    elif role_id == 4:  # Agent
        my_team = Users.objects.filter(id=user_id)  # Agent can only see themselves

    elif role_id == 5:  # Manager
        team_leaders = Users.objects.filter(role_id=6, senior_id=user_id)
        relationship_managers = Users.objects.filter(role_id=7, senior_id__in=team_leaders.values_list('id', flat=True))

        user_ids = list(team_leaders.values_list('id', flat=True)) + \
                   list(relationship_managers.values_list('id', flat=True)) 
        my_team = Users.objects.filter(id__in=user_ids)

    elif role_id == 6:  # Team Leader
        relationship_managers = Users.objects.filter(role_id=7, senior_id=user_id)
        user_ids = list(relationship_managers.values_list('id', flat=True))
        my_team = Users.objects.filter(id__in=user_ids)

    elif role_id == 7:  # Relationship Manager
        my_team = Users.objects.filter(id=user_id)

    else:
        my_team = Users.objects.all()

    return render(request, 'members/my-team.html', {'my_team': my_team})