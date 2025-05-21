from django.http import HttpResponse
from django.contrib.auth.hashers import make_password
from django.contrib.auth import update_session_auth_hash
from django.shortcuts import render,redirect, get_object_or_404
from django.contrib import messages
from django.template import loader
from ..models import Commission,Users, PolicyUploadDoc,Branch,PolicyInfo,PolicyDocument, DocumentUpload, FranchisePayment, InsurerPaymentDetails, PolicyVehicleInfo, AgentPaymentDetails, UploadedExcel, UploadedZip
from ..models import BulkPolicyLog,ExtractedFile, BqpMaster, InsurerBulkUploadPolicyLog
from empPortal.model import Referral
from empPortal.model import CommissionUpdateLog
from django.db.models import Q
from empPortal.model import BankDetails
from ..forms import DocumentUploadForm
from django.contrib.auth import authenticate, login ,logout
from django.core.files.storage import FileSystemStorage
import re,openpyxl
from django.db import IntegrityError
import requests
from fastapi import FastAPI, File, UploadFile
import fitz
import openai
from django.utils import timezone

import time
import json
from django.http import JsonResponse
import os
import zipfile
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db import connection
from urllib.parse import quote
from urllib.parse import urljoin
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from urllib.parse import unquote
from django.views.decorators.csrf import csrf_exempt
from pprint import pprint 
import pdfkit, logging
from django.templatetags.static import static 
from django.template.loader import render_to_string
from django_q.tasks import async_task
import pandas as pd
from ..models import PartnerUploadExcel, InsurerBulkUpload
from collections import Counter
from io import BytesIO
from ..utils import getUserNameByUserId, policy_product
logging.getLogger('faker').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)
OPENAI_API_KEY = settings.OPENAI_API_KEY
from django.core.paginator import Paginator
from dateutil import parser

from django.db.models import Q, F, Value
from django.db.models.functions import Lower
import json
app = FastAPI()

# views.py
from ..utils import send_sms_post
from datetime import datetime

def parse_date(date_str):
    try:
        # Try parsing with common datetime format first
        parsed = datetime.strptime(date_str, "%b. %d, %Y, %I:%M %p")
        return parsed.date()
    except ValueError:
        try:
            # Try ISO format fallback
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return None  # You can handle invalid dates as needed
        
from empPortal.model import Referral

logger = logging.getLogger(__name__)


# def get_campaign_log(request):
#     # Retrieve all policy logs ordered by creation time (newest first)
#     logs = InsurerBulkUpload.objects.all().order_by('-uploaded_at')

#     return render(request, 'policy-payment/campaign-log-index.html', {'uploads': logs})

def ajax_get_campaigns(request):
    query = request.GET.get("q", "")
    campaigns = (
        InsurerBulkUpload.objects
        .filter(campaign_name__icontains=query)
        .values("campaign_name")
        .distinct()
        .order_by("campaign_name")[:20]
    )
    data = [{"name": c["campaign_name"]} for c in campaigns]
    return JsonResponse(data, safe=False)


def get_campaign_log(request):
    q = request.GET.get("q", "")
    uploads = InsurerBulkUpload.objects.prefetch_related('logs').order_by('-uploaded_at')
    if q:
        uploads = uploads.filter(campaign_name__icontains=q)
    return render(request, 'policy-payment/campaign-log-index.html', {'uploads': uploads})


def view_payment_update_log(request):
    # Retrieve all policy logs ordered by creation time (newest first)
    logs = InsurerBulkUpload.objects.all().order_by('-uploaded_at')

    return render(request, 'policy-payment/view-payment-log-index.html', {'logs': logs})

def insurer_payment(request):
    if not request.user.is_authenticated:
        return redirect('login')

    if request.method == "POST" and request.FILES.get("excel_file"):
        excel_file = request.FILES["excel_file"]
        campaign_name = request.POST.get("campaign_name", "").strip()

        if not excel_file.name.lower().endswith((".xlsx", ".xls")):
            messages.error(request, "Only Excel files (.xlsx, .xls) are allowed!")
            return redirect("insurer-payment")

        instance = InsurerBulkUpload.objects.create(
            file=excel_file,
            file_name=excel_file.name,
            file_url=excel_file.name,
            campaign_name=campaign_name,
            created_by=request.user,
        )

        # You can make this async using async_task if needed
        process_insurer_bulk_excel(instance.id, request.user)

        messages.success(request, "Excel uploaded and is being processed.")
        return redirect("insurer-payment")

    return render(request, 'policy-payment/insurer-payment.html')


import re


def process_insurer_bulk_excel(file_id, user):
    try:
        logger.info(f"Starting insurer Excel processing for file ID: {file_id}")

        # Retrieve the InsurerBulkUpload instance
        instance = InsurerBulkUpload.objects.get(id=file_id)
        logger.info(f"Loaded Excel file: {instance.file.path}")

        # Load the Excel workbook and sheet
        wb = openpyxl.load_workbook(instance.file.path)
        sheet = wb.active

        success = error = 0
        total_rows = sheet.max_row - 1
        logger.info(f"Total rows (excluding header): {total_rows}")

        for idx, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
            logger.info(f"Processing row {idx}")

            try:
                # Extract values
                policy_no, receive_amount, balance_amount = [str(cell).strip() if cell else '' for cell in row]
                logger.debug(f"Row {idx} - Extracted: policy_no={policy_no}, receive_amount={receive_amount}, balance_amount={balance_amount}")

                if not policy_no:
                    logger.warning(f"Row {idx}: Missing policy number.")
                    # Log failure for this row
                    InsurerBulkUploadPolicyLog.objects.create(
                        upload=instance,
                        policy_number=policy_no,
                        status='failed',
                        message="Missing policy number."
                    )
                    error += 1
                    continue

                # Normalize the policy number
                normalized_policy_no = re.sub(r'[^a-zA-Z0-9]', '', policy_no.strip().lower())
                logger.debug(f"Row {idx}: Normalized policy number: {normalized_policy_no}")

                # First, try to find a match by normalizing the DB records
                policy = None
                for db_policy in PolicyDocument.objects.all():
                    db_normalized = re.sub(r'[^a-zA-Z0-9]', '', db_policy.policy_number.strip().lower())
                    if db_normalized == normalized_policy_no:
                        policy = db_policy
                        break

                # If not found, fallback to exact match
                if not policy:
                    logger.debug(f"Row {idx}: Trying exact match for original policy number.")
                    policy = PolicyDocument.objects.filter(policy_number__iexact=policy_no).first()

                if not policy:
                    logger.warning(f"Row {idx}: Policy not found for policy number: {policy_no}")
                    # Log failure for this row
                    InsurerBulkUploadPolicyLog.objects.create(
                        upload=instance,
                        policy_number=policy_no,
                        status='failed',
                        message="Policy not found in the database."
                    )
                    error += 1
                    continue

                # Create or update InsurerPaymentDetails
                payment, created = InsurerPaymentDetails.objects.get_or_create(
                    policy=policy,
                    policy_number=policy_no,
                    defaults={
                        'insurer_receive_amount': receive_amount,
                        'insurer_balance_amount': balance_amount,
                        'updated_by': user,
                    }
                )

                if created:
                    logger.info(f"Row {idx}: Created new InsurerPaymentDetails entry for policy: {policy_no}")
                else:
                    logger.info(f"Row {idx}: Updating existing InsurerPaymentDetails for policy: {policy_no}")
                    payment.insurer_receive_amount = receive_amount
                    payment.insurer_balance_amount = balance_amount
                    payment.updated_by = user
                    payment.updated_at = timezone.now()
                    payment.save()
                    logger.debug(f"Row {idx}: Updated fields saved")

                # Log success for this policy
                InsurerBulkUploadPolicyLog.objects.create(
                    upload=instance,
                    policy_number=policy_no,
                    status='success',
                    message=f"Receive Amount: {receive_amount}, Balance Amount: {balance_amount}"
                )

                success += 1

            except Exception as e:
                logger.error(f"Row {idx}: Exception occurred - {e}")
                # Log failure for this row
                InsurerBulkUploadPolicyLog.objects.create(
                    upload=instance,
                    policy_number=policy_no,
                    status='failed',
                    message=str(e)
                )
                error += 1

        # Update upload status
        logger.info(f"Updating upload instance with results: Success={success}, Errors={error}")
        instance.total_rows = total_rows
        instance.success_rows = success
        instance.error_rows = error
        instance.valid_rows = success
        instance.invalid_rows = error
        instance.is_processed = True
        instance.save()

        logger.info(f"Finished processing insurer Excel - Success: {success}, Errors: {error}")

    except Exception as e:
        logger.exception(f"Fatal error while processing file ID {file_id}: {e}")


def campaign_policy_logs(request, upload_id):
    """
    View to show all policy-level logs for a specific InsurerBulkUpload (campaign).
    """
    # Get the specific campaign upload instance
    upload = get_object_or_404(InsurerBulkUpload, id=upload_id)

    # Get all policy logs linked to this upload
    logs = InsurerBulkUploadPolicyLog.objects.filter(upload=upload).order_by('-created_at')

    return render(request, 'policy-payment/campaign-log-list.html', {
        'upload': upload,
        'logs': logs,
    })

def log_commission_update(commission_type, policy_id, policy_number, updated_by_id, updated_from, data):
    CommissionUpdateLog.objects.create(
        commission_type=commission_type,
        policy_id=policy_id,
        policy_number=policy_number,
        updated_by_id=updated_by_id,
        updated_from=updated_from,
        updated_data=data,
    )