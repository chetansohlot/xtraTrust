import os
import re
import json
import time
import zipfile
import logging
from io import BytesIO
from pprint import pprint
from collections import Counter
from datetime import datetime, timedelta
from urllib.parse import quote, unquote, urljoin

import requests
import pandas as pd
import openpyxl
import pdfkit
import fitz  # PyMuPDF
import openai
from fastapi import FastAPI, File, UploadFile

from django.conf import settings
from django.db import connection, IntegrityError
from django.db.models import Q, Count, OuterRef, Subquery
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage, default_storage
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template import loader
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from decimal import Decimal, InvalidOperation

from django_q.tasks import async_task

from ..models import (
    Commission, Users, PolicyUploadDoc, Branch, PolicyInfo, PolicyDocument,
    DocumentUpload, FranchisePayment, InsurerPaymentDetails, PolicyVehicleInfo,
    AgentPaymentDetails, UploadedExcel, UploadedZip, BulkPolicyLog, ExtractedFile,
    BqpMaster, SingleUploadFile
)
from ..model import Insurance
from empPortal.model import Referral, BankDetails, Partner
from empPortal.model import XtClientsBasicInfo
from empPortal.model.insurer import WimMasterInsurer
from empPortal.model.tpas import WimMasterTPA
from empPortal.model.wimGmcPolicyInfo import WimGmcPolicyInfo
from empPortal.model.wimMasterPolicyTypes import MasterPolicyType
from empPortal.model.gmcPolicyHighlights import GmcPolicyHighlights
from empPortal.model.gmcPolicyCoverages import GmcPolicyCoverage
from empPortal.model.gmcPolicyExclusions import GmcPolicyExclusions

from ..forms import DocumentUploadForm

from ..utils import getUserNameByUserId, policy_product, send_sms_post

app = FastAPI()

def index(request):
    if not request.user.is_authenticated or not request.user.is_active:
        messages.error(request, 'Please Login First')
        return redirect('login')
    
    policies = WimGmcPolicyInfo.objects.all()
    total_count = WimGmcPolicyInfo.objects.count()
    
    return render(request, 'policy/index.html', {"policies": policies, 'total_count': total_count})

def createPolicy(request, ref_id=None):
    if not request.user.is_authenticated and request.user.is_active != 1:
        messages.error(request,'Please Login First')
        return redirect('login')
    
    policy = None
    if ref_id:
        policy = WimGmcPolicyInfo.objects.filter(gmc_reference_id=ref_id).last()
        
    clients_list = XtClientsBasicInfo.objects.filter(active='active')
    insurer_list = WimMasterInsurer.objects.filter(master_insurer_is_active=True)
    tpa_list = WimMasterTPA.objects.filter(master_tpa_is_active=True)
    policy_type_list = MasterPolicyType.objects.filter(master_policy_type_is_active=True)
    return render(request,'policy/create-policy.html',{"clients_list":clients_list,"insurer_list":insurer_list,'tpa_list':tpa_list,'policy_type_list':policy_type_list,'policy':policy})

def savePolicyInfo(request):
    if not request.user.is_authenticated or not request.user.is_active:
        messages.error(request, 'Please Login First')
        return redirect('login')

    required_fields = {
        'client': 'Client is required',
        'insurer': 'Insurer is required',
        'tpa': 'TPA is required',
        'policy_type': 'Policy type is required',
        'policy_number': 'Policy number is required',
        'product_name': 'Product name is required',
        'claim_process_mode': 'Claim process mode is required',
        'policy_start_date': 'Policy start date is required',
        'policy_end_date': 'Policy end date is required',
        'policy_tenure': 'Policy tenure is required',
        'total_sum_insured': 'Total sum insured is required',
        'premium_amount': 'Premium is required',
        'gst_amount': 'GST amount is required',
        'total_lives': 'Total lives is required',
        'total_employee': 'Total employee count is required',
        'total_dependent': 'Total dependent count is required',
        'total_spouse': 'Total spouse count is required',
        'total_child': 'Total child count is required',
        'remark': 'Remark is required',
    }

    data = {key: request.POST.get(key) for key in required_fields}
    missing = [field for field, value in data.items() if not value]

    for field in missing:
        messages.error(request, required_fields[field])

    if missing:
        return redirect(request.META.get('HTTP_REFERER', 'policy-view'))

    try:
        policy_id = int(request.POST.get('policy_id'))
        if policy_id:
            policy_data = get_object_or_404(WimGmcPolicyInfo, id=policy_id)
            policy_data.master_insurer_id=data['insurer']
            policy_data.master_tpa_id=data['tpa']
            policy_data.master_policy_type_id=data['policy_type']
            policy_data.gmc_policy_number=data['policy_number']
            policy_data.gmc_product_name=data['product_name']
            policy_data.gmc_claim_process_mode=data['claim_process_mode']
            policy_data.gmc_policy_start_date=data['policy_start_date']
            policy_data.gmc_policy_end_date=data['policy_end_date']
            policy_data.gmc_policy_term_months=data['policy_tenure']
            policy_data.gmc_policy_total_sum_insured=data['total_sum_insured']
            policy_data.gmc_policy_premium_amount=data['premium_amount']
            policy_data.gmc_policy_gst_amount=data['gst_amount']
            policy_data.gmc_policy_total_lives=data['total_lives']
            policy_data.gmc_policy_total_employees=data['total_employee']
            policy_data.gmc_policy_total_dependents=data['total_dependent']
            policy_data.gmc_policy_total_spouses=data['total_spouse']
            policy_data.gmc_policy_total_childs=data['total_child']
            policy_data.gmc_policy_remarks=data['remark']
            policy_data.save()
            messages.success(request, "Policy updated successfully.")
        else:
            policy_data = WimGmcPolicyInfo.objects.create(
                client_id=data['client'],
                master_insurer_id=data['insurer'],
                master_tpa_id=data['tpa'],
                master_policy_type_id=data['policy_type'],
                gmc_policy_number=data['policy_number'],
                gmc_product_name=data['product_name'],
                gmc_claim_process_mode=data['claim_process_mode'],
                gmc_policy_start_date=data['policy_start_date'],
                gmc_policy_end_date=data['policy_end_date'],
                gmc_policy_term_months=data['policy_tenure'],
                gmc_policy_total_sum_insured=data['total_sum_insured'],
                gmc_policy_premium_amount=data['premium_amount'],
                gmc_policy_gst_amount=data['gst_amount'],
                gmc_policy_total_lives=data['total_lives'],
                gmc_policy_total_employees=data['total_employee'],
                gmc_policy_total_dependents=data['total_dependent'],
                gmc_policy_total_spouses=data['total_spouse'],
                gmc_policy_total_childs=data['total_child'],
                gmc_policy_remarks=data['remark'],
            )
            messages.success(request, "Policy information saved successfully.")
        
        return redirect('policy-view')
    except Exception as e:
        messages.error(request, f"Failed to save policy: {str(e)}")

    return redirect('policy-view')

def createPolicyHighlights(request,ref_id):
    if not request.user.is_authenticated and request.user.is_active != 1:
        messages.error(request,'Please Login First')
        return redirect('login')
    
    policy_data = WimGmcPolicyInfo.objects.filter(gmc_reference_id=ref_id).last()
    policy_highlights = GmcPolicyHighlights.objects.filter(policy_id=policy_data.id,status=True)
    return render(request,'policy/create-highlights-policy.html',{"policy_data":policy_data,"policy_highlights":policy_highlights})

def savePolicyHighlight(request):
    if not request.user.is_authenticated and request.user.is_active != 1:
        messages.error(request,'Please Login First')
        return redirect('login')
    
    if request.method == 'POST':
        policy_id = request.POST.get('policy_id')
        category = request.POST.get('category')
        description = request.POST.get('description')

        required_fields = {
            'category': 'Category is required',
            'description': 'Description is required',
        }

        data = {key: request.POST.get(key) for key in required_fields}
    
        missing = [field for field, value in data.items() if not value]

        for field in missing:
            messages.error(request, required_fields[field])

        if missing:
            return redirect(request.META.get('HTTP_REFERER', 'policy-view'))
        
        try:
            policy = get_object_or_404(WimGmcPolicyInfo, id=policy_id)
            highlight = GmcPolicyHighlights(policy_id=policy_id, category=category, highlight=description, created_by_id= request.user.id)
            highlight.save()

            messages.success(request, "Policy highlight saved successfully.")
            return redirect('create-policy-highlights',ref_id=policy.gmc_reference_id)
        except Exception as e:
            messages.error(request, f"Failed to save policy: {str(e)}")

    return redirect('policy-view')

def deletePolicyHighlight(request, ref_id):
    highlight = get_object_or_404(GmcPolicyHighlights, highlight_ref_id=ref_id)
    highlight.status = False
    highlight.save()
    
    messages.success(request, "Policy highlight deleted successfully.")
    return redirect(request.META.get('HTTP_REFERER', 'policy-view'))

def createPolicyCoverages(request,ref_id):
    if not request.user.is_authenticated and request.user.is_active != 1:
        messages.error(request,'Please Login First')
        return redirect('login')
    
    policy_data = WimGmcPolicyInfo.objects.filter(gmc_reference_id=ref_id).last()
    policy_coverages = GmcPolicyCoverage.objects.filter(policy_id=policy_data.id,status=True)
    
    return render(request,'policy/create-coverage-policy.html',{"policy_data":policy_data,"policy_coverages":policy_coverages})

def savePolicyCoverage(request):
    if request.method == 'POST':
        policy_id = request.POST.get('policy_id')
        coverage_item = request.POST.get('coverage_item')
        description = request.POST.get('description')
        sum_insured = request.POST.get('sum_insured')

        if sum_insured:
            try:
                sum_insured = Decimal(sum_insured)
            except (InvalidOperation, TypeError):
                messages.error(request, "Sum Insured must be a valid number.")
                return redirect(request.META.get('HTTP_REFERER', '/'))
        else:
            sum_insured = None
        
        required_fields = {
            'coverage_item': 'Coverage Item is required',
            'description': 'Description is required',
        }

        data = {key: request.POST.get(key) for key in required_fields}
    
        missing = [field for field, value in data.items() if not value]

        for field in missing:
            messages.error(request, required_fields[field])

        if missing:
            return redirect(request.META.get('HTTP_REFERER', 'policy-view'))

        policy = get_object_or_404(WimGmcPolicyInfo, id=policy_id)

        GmcPolicyCoverage.objects.create(
            policy_id=policy_id,
            coverage_item=coverage_item,
            coverage_description=description,
            sum_insured=sum_insured,
            created_by_id = request.user.id
        )

        messages.success(request, "Policy coverage saved successfully.")
        return redirect(request.META.get('HTTP_REFERER', '/'))

    return redirect('policy-view')


def deletePolicyCoverage(request, ref_id):
    coverage = get_object_or_404(GmcPolicyCoverage, coverage_ref_id=ref_id)
    coverage.status = False
    coverage.save()
    
    messages.success(request, "Policy coverage deleted successfully.")
    return redirect(request.META.get('HTTP_REFERER', 'policy-view'))


def createPolicyExclusions(request,ref_id):
    if not request.user.is_authenticated and request.user.is_active != 1:
        messages.error(request,'Please Login First')
        return redirect('login')
    
    policy_data = WimGmcPolicyInfo.objects.filter(gmc_reference_id=ref_id).last()
    policy_exclusions = GmcPolicyExclusions.objects.filter(policy_id=policy_data.id,status=True)
    
    return render(request,'policy/create-exclusions-policy.html',{"policy_data":policy_data,"policy_exclusions":policy_exclusions})

def savePolicyExclusion(request):
    if request.method == 'POST':
        policy_id = request.POST.get('policy_id')
        exclusion_title = request.POST.get('exclusion_title')
        description = request.POST.get('description')
        
        required_fields = {
            'exclusion_title': 'Exclusion Item is required',
            'description': 'Description is required',
        }

        data = {key: request.POST.get(key) for key in required_fields}
    
        missing = [field for field, value in data.items() if not value]

        for field in missing:
            messages.error(request, required_fields[field])

        if missing:
            return redirect(request.META.get('HTTP_REFERER', 'policy-view'))
        
        try:
            policy_id = request.POST.get('policy_id')
            exclusion_title = request.POST.get('exclusion_title')
            description = request.POST.get('description')

            policy = get_object_or_404(WimGmcPolicyInfo, id=policy_id)

            GmcPolicyExclusions.objects.create(
                policy_id=policy_id,
                exclusion_title=exclusion_title,
                exclusion_description=description,
                created_by_id=request.user.id
            )

            messages.success(request, "Policy exclusion saved successfully.")
        except Exception as e:
            messages.error(request, f"Failed to save policy exclusion: {str(e)}")
            
        return redirect(request.META.get('HTTP_REFERER', '/'))

    return redirect('policy-view')

def deletePolicyExclusion(request, ref_id):
    exclusion = get_object_or_404(GmcPolicyExclusions, exclusion_ref_id=ref_id)
    exclusion.status = False
    exclusion.save()
    
    messages.success(request, "Policy exclusion deleted successfully.")
    return redirect(request.META.get('HTTP_REFERER', 'policy-view'))


def parse_date(date_str):
    try:
        parsed = datetime.strptime(date_str, "%b. %d, %Y, %I:%M %p")
        return parsed.date()
    except ValueError:
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return None  # You can handle invalid dates as needed
        

def edit_policy(request, policy_id):
    if not request.user.is_authenticated and request.user.is_active != 1:
        messages.error(request,'Please Login First')
        return redirect('login')
    
    if request.method == 'POST':
        policy_id = request.POST.get('policy_id')
        policy_number = request.POST.get('policy_number')

        # Try to find another policy with the same number
        policy = PolicyInfo.objects.filter(
            policy_number=policy_number,policy_id=policy_id
        ).first()

        if policy:
            pass
        else:
            policy = PolicyInfo()
            policy.policy_id = policy_id

        # Basic Policy
        policy.policy_number = policy_number
        policy.policy_issue_date = request.POST.get('policy_issue_date')
        policy.policy_start_date = request.POST.get('policy_start_date')
        policy.policy_expiry_date = request.POST.get('policy_expiry_date')

        # Insured Details
        policy.insurer_name = request.POST.get('owner_name')
        policy.insured_name = request.POST.get('holder_name')
        policy.insured_mobile = request.POST.get('insured_mobile')
        policy.insured_email = request.POST.get('insured_email')
        policy.insured_address = request.POST.get('insured_address')
        policy.insured_pan = request.POST.get('insured_pan')
        policy.insured_aadhaar = request.POST.get('insured_aadhaar')

        # Policy Details
        policy.insurance_company = request.POST.get('insurance_company')
        policy.service_provider = request.POST.get('location')
        policy.insurer_contact_name = request.POST.get('owner_name')
        # policy.bqp = request.POST.get('father_name')
        # policy.pos_name = request.POST.get('vehicle_owner_number')
        policy.branch_id = request.POST.get('registration_city')
        policy.branch_name = request.POST.get('registration_city')
        policy.supervisor_name = request.POST.get('supervisor_name')
        policy.policy_type = request.POST.get('policy_type')
        policy.policy_plan = request.POST.get('policy_duration')
        policy.sum_insured = request.POST.get('idv_value')
        policy.od_premium = request.POST.get('od_premium')
        policy.tp_premium = request.POST.get('tp_premium')
        policy.pa_count = request.POST.get('pa_count', '0')
        policy.pa_amount = request.POST.get('pa_amount', '0.00')
        policy.driver_count = request.POST.get('driver_count', '0')
        policy.driver_amount = request.POST.get('driver_amount', '0.00')
        # policy.referral_by = request.POST.get('referral_by')
        policy.fuel_type = request.POST.get('fuel_type')
        policy.be_fuel_amount = request.POST.get('be_fuel_amount')
        policy.gross_premium = request.POST.get('gross_premium')
        policy.net_premium = request.POST.get('net_premium')
        policy.gst_premium = request.POST.get('gst_premium')

        policy.save()
        messages.success(request, "Policy Updated successfully!")
        
        if request.user.department_id and request.user.department_id == "2":
            return redirect('edit-agent-payment-info',policy_id=quote(policy_id, safe=''))
        else:
            return redirect('edit-policy-vehicle-details', policy_id=quote(policy_id, safe=''))

def none_if_blank(value):
    return value if value and value.strip() else None



def operator_verify_policy(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            policy_id = data.get('policy_id')
            remark = data.get('remark', '')
            status = data.get('status')  # Expecting '1' for Approved, '2' for Rejected
            type = data.get('type')  # 'operator' or 'quality'

            if not policy_id:
                return JsonResponse({'success': False, 'error': 'Policy ID is required.'})
            if status not in ['1', '2']:
                return JsonResponse({'success': False, 'error': 'Invalid status. Must be "1" (Approved) or "2" (Rejected).'})

            policy = PolicyDocument.objects.filter(id=policy_id).first()
            if not policy:
                return JsonResponse({'success': False, 'error': 'Policy not found.'})

            if type == 'operator':
                policy.operator_verification_status = status
                policy.operator_policy_verification_by = request.user.id
                policy.operator_remark = remark
            elif type == 'quality':
                policy.quality_check_status = status
                policy.quality_policy_check_by = request.user.id
                policy.quality_remark = remark
                if status == '2':
                    policy.operator_verification_status = '0'

            else:
                return JsonResponse({'success': False, 'error': 'Invalid type.'})

            policy.save()

            status_msg = 'approved' if status == '1' else 'rejected'
            return JsonResponse({'success': True, 'message': f'Policy {status_msg} successfully.'})

        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON.'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Invalid request method.'})

def viewPolicy(request,id):
    if not request.user.is_authenticated and request.user.is_active !=1:
        messages.error(request, "Please Login First")
        return redirect('login')
    try:
        policy_doc=get_object_or_404(PolicyDocument,id=id)
        policy_number=policy_doc.policy_number

        policy_info =PolicyInfo.objects.filter(policy_id=policy_doc, policy_number=policy_number).select_related('bqp','branch').order_by('-id').first()

         # Get POS user (if pos_name stores user ID)
        pos_user = None
        if policy_info and policy_info.pos_name:
            try:
                pos_user = Users.objects.get(id=policy_info.pos_name)
            except Users.DoesNotExist:
                pos_user = None

        # policy_vechicle details #
        policy_vehicle =PolicyVehicleInfo.objects.filter(policy_id=id, policy_number=policy_number).first()

        #policy agents details #
        # policy_agent_details =AgentPaymentDetails.objects.filter(policy_id=id).select_related('referral').first()
        # print(policy_agent_details)

        # Agent payment info
        policy_agent_details = AgentPaymentDetails.objects.filter(policy=policy_doc).select_related('referral', 'policy').first()
        
        #policy_upload docs #
        policy_upload_docs=PolicyUploadDoc.objects.filter(policy_id=id).first()

        # Insurer & Franchise payments
        policy_insurer_details=InsurerPaymentDetails.objects.filter(policy_id=id).first()
        policy_franchise_details=FranchisePayment.objects.filter(policy_id=id).first()



        context={
            'policy_doc':policy_doc,
            'policy_info' : policy_info,
            'policy_vehicle':policy_vehicle,
            'policy_agent_details':policy_agent_details,
            'policy_doc': policy_doc,
            'policy_upload_docs' :policy_upload_docs,
            'policy_insurer_details':policy_insurer_details,
            'policy_franchise_details':policy_franchise_details, 
            'pos_user':pos_user,
        }
        return render(request, 'policy/view-policy.html',context)
    
    except Exception as e:
        messages.error(request, f"Something went wrong: {str(e)}")
        return redirect('policy-data') 
    

def edit_vehicle_details(request, policy_id):
    
    if not request.user.is_authenticated and request.user.is_active != 1:
        messages.error(request, "Please Login First")
        return redirect('login')
    
    policy_id = policy_id
    policy_data = PolicyDocument.objects.filter(id=policy_id).first()
    policy_no = policy_data.policy_number
    # decoded_policy_no = unquote(policy_no)
    # policy = get_object_or_404(PolicyInfo, policy_number=decoded_policy_no)
    policy = PolicyInfo.objects.filter(policy_id=policy_id,policy_number=policy_no).last()
    policy_no = policy.policy_number
    if not policy:
        return redirect('policy-data')
    
    policy_id = request.POST.get('policy_id',policy_id)
        
    vehicle = PolicyVehicleInfo.objects.filter(policy_id=policy_id,policy_number=policy_no).last()
        
    if request.method == 'POST':
        if not vehicle:
            vehicle = PolicyVehicleInfo(policy_number=policy.policy_number, policy_id=policy_id)
    
        vehicle.vehicle_type = none_if_blank(request.POST.get('vehicle_type'))
        vehicle.vehicle_make = none_if_blank(request.POST.get('vehicle_make'))
        vehicle.vehicle_model = none_if_blank(request.POST.get('vehicle_model'))
        vehicle.vehicle_variant = none_if_blank(request.POST.get('vehicle_variant'))
        vehicle.fuel_type = none_if_blank(request.POST.get('fuel_type'))
        vehicle.gvw = none_if_blank(request.POST.get('gvw'))
        vehicle.cubic_capacity = none_if_blank(request.POST.get('cubic_capacity'))
        vehicle.seating_capacity = none_if_blank(request.POST.get('seating_capacity'))
        vehicle.registration_number = none_if_blank(request.POST.get('vehicle_reg_no'))
        vehicle.engine_number = none_if_blank(request.POST.get('engine_number'))
        vehicle.chassis_number = none_if_blank(request.POST.get('chassis_number'))
        vehicle.manufacture_year = none_if_blank(request.POST.get('mgf_year'))
        vehicle.ncb = none_if_blank(request.POST.get('ncb'))
        vehicle.save()
        messages.success(request, "Policy Vehicle details Updated successfully!")

        return redirect('edit-policy-docs', policy_id=quote(policy_id, safe=''))

    pdf_path = get_pdf_path(request, policy_data.filepath if policy_data else None)
    extracted_data = {}
    if policy_data and policy_data.extracted_text:
        if isinstance(policy_data.extracted_text, str):
            try:
                extracted_data = json.loads(policy_data.extracted_text)
            except json.JSONDecodeError:
                extracted_data = {}
        elif isinstance(policy_data.extracted_text, dict):
            extracted_data = policy_data.extracted_text  # already a dict

    return render(request, 'policy/edit-policy-vehicle.html', {
        'policy': policy,
        'policy_data': policy_data,
        'pdf_path': pdf_path,
        'extracted_data': extracted_data,
        'vehicle': vehicle
    })

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

def edit_policy_docs(request, policy_id):
    if not request.user.is_authenticated and request.user.is_active != 1:
        messages.error(request, "Please Login First")
        return redirect('login')
    
    policy_id = unquote(policy_id)
    policy_data = PolicyDocument.objects.filter(id=policy_id).first()
    policy = PolicyInfo.objects.filter(policy_id=policy_id,policy_number=policy_data.policy_number).last()
    
    
    try:
        doc_data = PolicyUploadDoc.objects.filter(policy_id=policy_id,policy_number=policy_data.policy_number).last()
    except PolicyUploadDoc.DoesNotExist:
        doc_data = PolicyUploadDoc(policy_id=policy_id,policy_number = policy_data.policy_number)
        
    # AJAX file upload
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        field_name = request.POST.get('field_name')

        if field_name and field_name in request.FILES:
            try:
                setattr(doc_data, field_name, request.FILES[field_name])
                doc_data.active = True
                doc_data.save()

                messages.success(request, "Doc Uploaded successfully!")

                return JsonResponse({'success': True})
            except Exception as e:
                return JsonResponse({'success': False, 'error': str(e)})

        return JsonResponse({'success': False, 'error': 'Invalid file field'})

    # Standard GET
    pdf_path = get_pdf_path(request, policy_data.filepath if policy_data else None)

    return render(request, 'policy/edit-policy-docs.html', {
        'policy': policy,
        'policy_data': policy_data,
        'pdf_path': pdf_path,
        'doc_data': doc_data
    })

def edit_agent_payment_info(request, policy_id):
    if not request.user.is_authenticated and request.user.is_active != 1:
        messages.error(request, "Please Login First")
        return redirect('login')

    policy_id = unquote(policy_id)

    policy_data = PolicyDocument.objects.filter(id=policy_id).first()

    policy = PolicyInfo.objects.filter(policy_id=policy_id,policy_number = policy_data.policy_number).last()
    if not policy:
        return redirect('policy-data')
    
    agent_payment = AgentPaymentDetails.objects.filter(policy_id=policy_id,policy_number = policy_data.policy_number).last()
    
    if request.method == 'POST':
        policy_id =  request.POST.get('policy_id')
        
        if not agent_payment:
            agent_payment = AgentPaymentDetails(policy_number=policy_data.policy_number,policy_id=policy_id)
        
        # agent_payment.agent_name = request.POST.get('agent_name')
        agent_payment.agent_name = request.POST.get('referral_by',None)
        agent_payment.referral_id = request.POST.get('referral_by',None)
        agent_payment.agent_payment_mod = request.POST.get('agent_payment_mod',None)
        agent_payment.transaction_id = request.POST.get('transaction_id',None)
        agent_payment.agent_payment_date = request.POST.get('agent_payment_date',None)
        agent_payment.agent_amount = request.POST.get('agent_amount',None)
        agent_payment.agent_remarks = request.POST.get('agent_remarks',None)
        if request.user.department_id and int(request.user.department_id) == 2:
            pass
        else:
            agent_payment.agent_od_comm = request.POST.get('agent_od_comm',None)
            agent_payment.agent_tp_comm = request.POST.get('agent_tp_comm',None)
            agent_payment.agent_net_comm = request.POST.get('agent_net_comm',None)
            agent_payment.agent_incentive_amount = request.POST.get('agent_incentive_amount',None)
            agent_payment.agent_tds = request.POST.get('agent_tds',None)
            agent_payment.agent_od_amount = request.POST.get('agent_od_amount',None)
            agent_payment.agent_net_amount = request.POST.get('agent_net_amount',None)
            agent_payment.agent_tp_amount = request.POST.get('agent_tp_amount',None)
            agent_payment.agent_total_comm_amount = request.POST.get('agent_total_comm_amount',None)
            agent_payment.agent_net_payable_amount = request.POST.get('agent_net_payable_amount',None)
            agent_payment.agent_tds_amount = request.POST.get('agent_tds_amount',None)
            agent_payment.updated_by = request.user
        
        agent_payment.save()
       
        policy.bqp_id = request.POST.get('bqp',None)
        policy.pos_name = request.POST.get('pos_name',None)
        policy.referral_by = request.POST.get('referral_by',None)
        policy.save()
            
        messages.success(request, "Policy Agent Payment Updated successfully!")
        return redirect('edit-insurer-payment-info', policy_id=quote(policy_id))

    referrals = Referral.objects.all().order_by('name')
    bqps = BqpMaster.objects.all().order_by('bqp_fname')
    pdf_path = get_pdf_path(request, policy_data.filepath)

    return render(request, 'policy/edit-agent-payment-info.html', {
        'policy': policy,
        'pdf_path': pdf_path,
        'policy_data': policy_data,
        'agent_payment': agent_payment,
        'bqps': bqps,
        'referrals':referrals
    })

def edit_insurer_payment_info(request, policy_id):
    if not request.user.is_authenticated and request.user.is_active != 1:
        messages.error(request, "Please Login First")
        return redirect('login')
    
    policy_id = unquote(policy_id)
        
    policy_data = PolicyDocument.objects.filter(id=policy_id).first()

    insurer_payment = InsurerPaymentDetails.objects.filter(policy_id=policy_id,policy_number = policy_data.policy_number).last()
    if request.method == 'POST':
        policy_id =  request.POST.get('policy_id')
        if insurer_payment is None:
            insurer_payment = InsurerPaymentDetails(policy_number=policy_data.policy_number, policy_id=policy_id)

        # Now safely update fields
        if request.user.department_id and int(request.user.department_id) == 2:
            insurer_payment.insurer_payment_mode = request.POST.get('insurer_payment_mode', None)
            insurer_payment.insurer_payment_date = request.POST.get('insurer_payment_date', None)
            insurer_payment.insurer_amount = request.POST.get('insurer_amount', None)
            insurer_payment.insurer_remarks = request.POST.get('insurer_remarks', None)
        
        else:
            insurer_payment.insurer_payment_mode = request.POST.get('insurer_payment_mode', None)
            insurer_payment.insurer_payment_date = request.POST.get('insurer_payment_date', None)
            insurer_payment.insurer_amount = request.POST.get('insurer_amount', None)
            insurer_payment.insurer_remarks = request.POST.get('insurer_remarks', None)

            insurer_payment.insurer_od_comm = request.POST.get('insurer_od_comm', None)
            insurer_payment.insurer_od_amount = request.POST.get('insurer_od_amount', None)

            insurer_payment.insurer_tp_comm = request.POST.get('insurer_tp_comm', None)
            insurer_payment.insurer_tp_amount = request.POST.get('insurer_tp_amount', None)

            insurer_payment.insurer_net_comm = request.POST.get('insurer_net_comm', None)
            insurer_payment.insurer_net_amount = request.POST.get('insurer_net_amount', None)

            insurer_payment.insurer_tds = request.POST.get('insurer_tds', None)
            insurer_payment.insurer_tds_amount = request.POST.get('insurer_tds_amount', None)

            insurer_payment.insurer_incentive_amount = request.POST.get('insurer_incentive_amount', None)
            insurer_payment.insurer_total_comm_amount = request.POST.get('insurer_total_comm_amount', None)
            insurer_payment.insurer_net_payable_amount = request.POST.get('insurer_net_payable_amount', None)

            insurer_payment.insurer_total_commission = request.POST.get('insurer_total_commission', None)
            insurer_payment.insurer_receive_amount = request.POST.get('insurer_receive_amount', None)
            insurer_payment.insurer_balance_amount = request.POST.get('insurer_balance_amount', None)

            insurer_payment.active = '1'
            insurer_payment.updated_by = request.user

        insurer_payment.save()

        if request.user.department_id and int(request.user.department_id) == 2:
            messages.success(request, "Policy Insurer Details Updated successfully!")
            return redirect('policy-data')
        
        messages.success(request, "Insurer Payment details updated successfully!")
        return redirect('edit-franchise-payment-info', policy_id=quote(policy_id))

    pdf_path = get_pdf_path(request, policy_data.filepath)

    try:
        policy = PolicyInfo.objects.filter(policy_id=policy_id,policy_number = policy_data.policy_number).last()
    except Exception as e:
        policy = None
        
    return render(request, 'policy/edit-insurer-payment-info.html', {
        'policy': policy,
        'policy_data': policy_data,
        'pdf_path': pdf_path,
        'insurer_payment': insurer_payment
    })

def edit_franchise_payment_info(request, policy_id):
    if not request.user.is_authenticated and request.user.is_active != 1:
        messages.error(request, "Please Login First")
        return redirect('login')
    
    policy_id = unquote(policy_id)
    policy_data = PolicyDocument.objects.filter(id=policy_id).first()
    
    try:
        policy = PolicyInfo.objects.filter(policy_id=policy_id,policy_number=policy_data.policy_number).last()
    except Exception as e:
        policy = None


    franchise_payment = FranchisePayment.objects.filter(policy_id=policy_id,policy_number=policy_data.policy_number).last()
    
    if request.method == 'POST':
        policy_id = request.POST.get('policy_id')
      
        if not franchise_payment:
            franchise_payment = FranchisePayment(policy_number=policy_data.policy_number, policy_id=policy_id)

        # Update fields from POST data
        franchise_payment.franchise_od_comm = request.POST.get('franchise_od_comm', None)
        franchise_payment.franchise_net_comm = request.POST.get('franchise_net_comm', None)
        franchise_payment.franchise_tp_comm = request.POST.get('franchise_tp_comm', None)
        franchise_payment.franchise_incentive_amount = request.POST.get('franchise_incentive_amount', None)
        franchise_payment.franchise_tds = request.POST.get('franchise_tds', None)

        franchise_payment.franchise_od_amount = request.POST.get('franchise_od_amount', None)
        franchise_payment.franchise_net_amount = request.POST.get('franchise_net_amount', None)
        franchise_payment.franchise_tp_amount = request.POST.get('franchise_tp_amount', None)
        franchise_payment.franchise_total_comm_amount = request.POST.get('franchise_total_comm_amount', None)
        franchise_payment.franchise_net_payable_amount = request.POST.get('franchise_net_payable_amount', None)
        franchise_payment.franchise_tds_amount = request.POST.get('franchise_tds_amount', None)

        # Set other fields
        franchise_payment.active = True
        franchise_payment.updated_by = request.user
        
        # Save the updated franchise_payment
        franchise_payment.save()

        # Show success message
        messages.success(request, "Franchise Payment details updated successfully!")
        return redirect('policy-data')

    pdf_path = get_pdf_path(request, policy_data.filepath)

    return render(request, 'policy/edit-franchise-payment-info.html', {
        'policy': policy,
        'policy_data': policy_data,
        'pdf_path': pdf_path,
        'franchise_payment': franchise_payment
    })
    
def editBulkPolicy(request):
    if not request.user.is_authenticated and request.user.is_active != 1:
        messages.error(request, "Please Login First")
        return redirect('login')
    
    return render(request,'policy/edit-bulk-policy.html')
    
def updateBulkPolicy(request):
    if not request.user.is_authenticated or request.user.is_active != 1:
        messages.error(request,'Please Login First')
        return redirect('login')
    
    if request.method == "POST" and request.FILES.get("file"):
        file = request.FILES["file"]
        camp_name = request.POST.get("camp_name")

        # Validate Excel file format
        if not file.name.lower().endswith(".xlsx"):
            messages.error(request, "Invalid file format. Only .xlsx files are allowed.")
            return redirect("edit-bulk-policy")

        # Validate size
        if file.size > 5 * 1024 * 1024:
            messages.error(request, "File too large. Maximum allowed size is 5 MB.")
            return redirect("edit-bulk-policy")

        if not camp_name:
            messages.error(request, "Campaign Name is mandatory.")
            return redirect("edit-bulk-policy")

        try:
            wb = openpyxl.load_workbook(file, data_only=True)
            sheet = wb.active
            total_rows = sheet.max_row - 1
        except Exception as e:
            messages.error(request, f"Error reading Excel file: {str(e)}")
            return redirect("edit-bulk-policy")

        # Save the file to model
        excelInstance = UploadedExcel.objects.create(
            file=file,
            campaign_name=camp_name,
            created_by=request.user,
            total_rows=total_rows
        )
         # Optionally: Trigger background task
        async_task('empPortal.tasks.updateBulkPolicies', excelInstance.id)

        messages.success(request, "Excel uploaded successfully. Processing started in background.")
        return redirect("edit-bulk-policy")

    return redirect("edit-bulk-policy")

def viewBulkUpdates(request):
    if not request.user.is_authenticated or request.user.is_active != 1:
        messages.error(request,'Please Login First')
        return redirect('login')
    
    id  = request.user.id
    
    # Fetch policies
    role_id = Users.objects.filter(id=id,status=1).values_list('role_id', flat=True).first()
    if role_id != 1:
        logs =  UploadedExcel.objects.filter(rm_id=id).exclude(rm_id__isnull=True).order_by('-id')
    else:
        logs = UploadedExcel.objects.all().order_by('-id')
    
    policy_files = PolicyDocument.objects.all()
    statuses = Counter(file.status for file in policy_files)

    # Ensure all statuses are included in the count, even if they're 0
    status_counts = {
        0: statuses.get(0, 0),
        1: statuses.get(1, 0),
        2: statuses.get(2, 0),
        3: statuses.get(3, 0),
        4: statuses.get(4, 0),
        5: statuses.get(5, 0),
        6: statuses.get(6, 0),
        7: statuses.get(7, 0),
    }

    return render(request,'policy/bulk-edit-logs.html',{
        'logs': logs,
        'status_counts': status_counts,
        'total_files': len(policy_files)
    })
        
def bulkPolicyMgt(request):
    if not request.user.is_authenticated and request.user.is_active != 1:
        return redirect('login')
    rms = Users.objects.all()
    product_types = policy_product()
    insurers = Insurance.objects.all().order_by('-created_at')

    return render(request,'policy/bulk-policy-mgt.html',{
        'insurers':insurers,
        'users':rms,
        'product_types':product_types
    })

def bulkBrowsePolicy(request):
    if request.user.is_authenticated:
        if request.method == "POST":
            if request.FILES.get("zip_file"):
                zip_file = request.FILES["zip_file"]
            else:
                zip_file = None
            camp_name = request.POST.get("camp_name")
            rm_id = request.POST.get("rm_id")
            insurance_company = request.POST.get("insurance_company")
            product_type = request.POST.get("product_type")
            # Validate ZIP file format
            if not zip_file or not zip_file.name.lower().endswith(".zip"):
                messages.error(request, "Invalid file format. Only ZIP files are allowed.")
            else:
                if zip_file.size > 50 * 1024 * 1024:
                    messages.error(request, "File too large. Maximum allowed size is 50 MB.")
                else:
                    try:
                        zip_bytes = BytesIO(zip_file.read())
                        with zipfile.ZipFile(zip_bytes) as zf:
                            file_list = zf.infolist()
                            
                            root_files = [f for f in file_list if not f.is_dir() and "/" not in f.filename and "\\" not in f.filename]
                            
                            total_files = len(root_files)
                            pdf_files = [f for f in root_files if f.filename.lower().endswith(".pdf")]
                            non_pdf_files = [f for f in root_files if not f.filename.lower().endswith(".pdf")]
                            
                            directories = [f for f in root_files if f.is_dir()]
                            pdf_count = len(pdf_files)
                            non_pdf_count = len(non_pdf_files)
                            
                            if directories:
                                messages.error(request, "ZIP must not contain any folders.")
                                for folder in directories:
                                    messages.error(request, f" - Folder: {folder.filename}")
                            if total_files > 50:
                                messages.error(request, "ZIP contains more than 50 files.")
                            if non_pdf_files:
                                messages.error(request, "ZIP must contain only PDF files.")
                    except zipfile.BadZipFile:
                        messages.error(request, "The uploaded ZIP file is corrupted or invalid.")
                        
                        
            if not camp_name:
                messages.error(request, "Campaign Name is mandatory.")
            if not product_type:
                messages.error(request, "Product Type is mandatory.")
            if messages.get_messages(request):
                return redirect('bulk-policy-mgt')
            rm_name = getUserNameByUserId(rm_id) if rm_id else None
            bulk_log_instance = BulkPolicyLog.objects.create(
                file=ContentFile(zip_bytes.getvalue(), name=zip_file.name),
                camp_name=camp_name,
                rm_id=rm_id,
                insurance_company_id=insurance_company,
                rm_name=rm_name,
                created_by=request.user,
                count_total_files=total_files,
                count_pdf_files=0,
                count_not_pdf=0,
                count_error_pdf_files=0,
                count_error_process_pdf_files=0,
                count_uploaded_files=0,
                count_duplicate_files=0,
                product_type=product_type,
                status=1
            )
            
            bulk_log_instance.file.save(zip_file.name, ContentFile(zip_bytes.getvalue()))
            bulk_log_instance.save()
            
            messages.success(request, "ZIP uploaded successfully. Processing started in background.")
            return redirect("bulk-upload-logs")
        else:
            return redirect("bulk-policy-mgt")
    else:
        return redirect('login')

def policyMgt(request):
    if not request.user.is_authenticated and request.user.is_active != 1:
        messages.error(request, "Please Login First")
        return redirect('login')
    product_types = policy_product()
    insurers = Insurance.objects.all().order_by('-created_at')

    return render(request,'policy/single-policy-upload.html',{'product_types':product_types, 'insurers':insurers})


# def browsePolicy(request):
#     if not request.user.is_authenticated and request.user.is_active != 1:
#         messages.error(request, "Please Login First")
#         return redirect('login')
#     if request.method == "POST" and request.FILES.get("image"):
#         image = request.FILES["image"]
#          # Validate ZIP file format
#         if not image.name.lower().endswith(".pdf"):
#             messages.error(request, "Invalid file format. Only pdf files are allowed.")
#             return redirect("policy-mgt")
        
#         if image.size > 2 * 1024 * 1024:  # 2MB = 1024*1024*2 bytes
#             messages.error(request, "File too large. Maximum allowed size is 2 MB.")
#             return redirect("policy-mgt")

#         fs = FileSystemStorage()
#         filename = fs.save(image.name, image)
#         filepath = fs.path(filename)
#         fileurl = fs.url(filename)
#         extracted_text = extract_text_from_pdf(filepath)
#         if "Error" in extracted_text:
#             messages.error(request, extracted_text)
#             return redirect('policy-mgt')
        
#         member_id = request.user.id
       
#         commision_rate = commisionRateByMemberId(member_id)
#         insurer_rate = insurercommisionRateByMemberId(1)
#         if commision_rate:
#             od_percentage = commision_rate.od_percentage
#             net_percentage = commision_rate.net_percentage
#             tp_percentage = commision_rate.tp_percentage
#         else:
#             od_percentage = 0.0
#             net_percentage = 0.0
#             tp_percentage = 0.0
            
#         if insurer_rate:
#             insurer_od_percentage = insurer_rate.od_percentage
#             insurer_net_percentage = insurer_rate.net_percentage
#             insurer_tp_percentage = insurer_rate.tp_percentage
#         else:
#             insurer_od_percentage = 0.0
#             insurer_net_percentage = 0.0
#             insurer_tp_percentage = 0.0

        
#         processed_text = process_text_with_chatgpt(extracted_text)
#         if "error" in processed_text:
#             PolicyDocument.objects.create(
#                 filename=image.name,
#                 extracted_text=processed_text,
#                 filepath=fileurl,
#                 rm_name=request.user.first_name,
#                 rm_id=request.user.id,
#                 od_percent=od_percentage,
#                 tp_percent=tp_percentage,
#                 net_percent=net_percentage,
#                 insurer_tp_commission   = insurer_tp_percentage,
#                 insurer_od_commission   = insurer_od_percentage,
#                 insurer_net_commission  = insurer_net_percentage,
#                 status=3,
#             )
            
#             messages.error(request, f"Failed to process policy")
#             return redirect('policy-mgt')
#         else:
#             policy_number = processed_text.get("policy_number", None)
#             if PolicyDocument.objects.filter(policy_number=policy_number).exists():
#                 messages.error(request, "Policy Number already exists.")
#                 return redirect('policy-mgt')
            
#             vehicle_number = re.sub(r"[^a-zA-Z0-9]", "", processed_text.get("vehicle_number", ""))
#             coverage_details = processed_text.get("coverage_details", [{}])
#             od_premium = coverage_details.get('own_damage', {}).get('premium', 0)
#             tp_premium = coverage_details.get('third_party', {}).get('premium', 0)
#             PolicyDocument.objects.create(
#                 filename=image.name,
#                 extracted_text=processed_text,
#                 filepath=fileurl,
#                 rm_name=request.user.full_name,
#                 rm_id=request.user.id,
#                 insurance_provider=processed_text.get("insurance_company", ""),
#                 vehicle_number=vehicle_number,
#                 policy_number=policy_number,
#                 policy_issue_date=processed_text.get("issue_date", ""),
#                 policy_expiry_date=processed_text.get("expiry_date", ""),
#                 policy_start_date=processed_text.get('start_date', ""),
#                 policy_period=processed_text.get("policy_period", ""),
#                 holder_name=processed_text.get("insured_name", ""),
#                 policy_total_premium=processed_text.get("gross_premium", 0),
#                 policy_premium=processed_text.get("net_premium", 0),
#                 sum_insured=processed_text.get("sum_insured", 0),
#                 coverage_details=processed_text.get("coverage_details", ""),
#                 payment_status='Confirmed',
#                 policy_type=processed_text.get('additional_details', {}).get('policy_type', ""),
#                 vehicle_type=processed_text.get('vehicle_details', {}).get('vehicle_type', ""),
#                 vehicle_make=processed_text.get('vehicle_details', {}).get('make', ""),                      
#                 vehicle_model=processed_text.get('vehicle_details', {}).get('model', ""),                      
#                 vehicle_gross_weight=processed_text.get('vehicle_details', {}).get('vehicle_gross_weight', ""),                     
#                 vehicle_manuf_date=processed_text.get('vehicle_details', {}).get('registration_year', ""),                      
#                 gst=processed_text.get('gst_premium', 0),                      
#                 od_premium=od_premium,
#                 tp_premium=tp_premium,
#                 od_percent=od_percentage,
#                 tp_percent=tp_percentage,
#                 net_percent=net_percentage,
#                 insurer_tp_commission   = insurer_rate.tp_percentage,
#                 insurer_od_commission   = insurer_rate.od_percentage,
#                 insurer_net_commission  = insurer_rate.net_percentage,

#                 status=6,
#             )
#             messages.success(request, "PDF uploaded and processed successfully.")
            
#         return redirect('policy-data')
    
#     else:
#         messages.error(request, "Please upload a PDF file.")

#     return redirect('policy-mgt')


def browsePolicy(request):
    if not request.user.is_authenticated and request.user.is_active != 1:
        messages.error(request, "Please Login First")
        return redirect('login')
    
    if request.method != "POST":
        return redirect('policy-mgt')
    
    if request.FILES.get("file"):
        file = request.FILES["file"]
    else:
        file = None
        
    product_type = request.POST.get("product_type")
    insurance_company = request.POST.get("insurance_company")
    if not file:
        messages.error(request, "Upload PDF file.")
        
    if not file or not file.name.lower().endswith(".pdf"):
        messages.error(request, "Invalid file format. Only PDF files are allowed.")
    else:
        if file.size > 2 * 1024 * 1024:
            messages.error(request, "File too large. Maximum allowed size is 2 MB.")
                        
    if not product_type:
        messages.error(request, "Product Type is mandatory.")

    if not insurance_company:
        messages.error(request, "Insurance Company is mandatory.")

        return redirect('policy-mgt')
    if messages.get_messages(request):
        return redirect('policy-mgt')
    
    single_policy = SingleUploadFile.objects.create(
        file_path=file,
        status=1,
        retry_source_count=0,
        product_type=product_type,
        insurance_company_id=insurance_company,
        retry_chat_response_count=0,
        retry_creating_policy_count=0,
        create_by=request.user
    )
    
    messages.success(request, "Pdf Uploaded Successfully")
    return redirect("policy-mgt")
        
def bulkPolicyView(request, id):
    if not request.user.is_authenticated or request.user.is_active != 1:
        return redirect('login')

    # Fetch policy documents based on bulk_log_id
    policy_files = ExtractedFile.objects.filter(bulk_log_ref_id=id)
    status_files = ExtractedFile.objects.filter(bulk_log_ref_id=id,is_failed = False)
    statuses = Counter(file.status for file in status_files)

    failed_files = ExtractedFile.objects.filter(bulk_log_ref_id=id,is_failed=True).count()
    # Ensure all statuses are included in the count, even if they're 0
    status_counts = {
        0: statuses.get(0, 0),
        1: statuses.get(1, 0),
        2: statuses.get(2, 0),
        3: statuses.get(3, 0),
        4: statuses.get(4, 0),
        5: statuses.get(5, 0),
        6: statuses.get(6, 0),
        7: statuses.get(7, 0),
    }

    return render(request, 'policy/extracted-files.html', {
        'files': policy_files,
        'total_files': len(policy_files),
        'log_id': id,
        'failed_files_count': failed_files,
        'status_counts': status_counts
    })

def bulkUploadLogs(request):
    if not request.user.is_authenticated or request.user.is_active != 1:
        messages.error(request,'Please Login First')
        return redirect('login')
    
    id  = request.user.id
        # Fetch policies
    role_id = Users.objects.filter(id=id,status=1).values_list('role_id', flat=True).first()
    if role_id != 1:
     logs =  BulkPolicyLog.objects.filter(rm_id=id).exclude(rm_id__isnull=True).order_by('-id')
    else:
      logs = BulkPolicyLog.objects.all().order_by('-id')
    
    policy_files = ExtractedFile.objects.all()
    statuses = Counter(file.status for file in policy_files)

    # Ensure all statuses are included in the count, even if they're 0
    status_counts = {
        0: statuses.get(0, 0),
        1: statuses.get(1, 0),
        2: statuses.get(2, 0),
        3: statuses.get(3, 0),
        4: statuses.get(4, 0),
        5: statuses.get(5, 0),
        6: statuses.get(6, 0),
        7: statuses.get(7, 0),
    }

    return render(request,'policy/bulk-upload-logs.html',{
        'logs': logs,
        'status_counts': status_counts,
        'total_files': len(policy_files)
    })

def policyData(request):
    if not request.user.is_authenticated:
        return redirect('login')
    user_id = request.user.id
    role_id = Users.objects.filter(id=user_id).values_list('role_id', flat=True).first()

    filters_q = Q(status=6) & Q(policy_number__isnull=False) & ~Q(policy_number='')
    if role_id != 1 and request.user.department_id != "5" and request.user.department_id != "3" and request.user.department_id != "2":
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

    user = request.user
    filters_q = Q(status=6) & Q(policy_number__isnull=False) & ~Q(policy_number='')

    if user.role_id != 1 and str(user.department_id) not in ["3", "5", "2"]:
        filters_q &= Q(rm_id=user.id)

    branch_id   = request.GET.get('branch_name', '')
    referral_id = request.GET.get('referred_by', '')
    
    if branch_id:
        filters_q &= Q(policy_info__branch_name=str(branch_id))
    if referral_id:
        filters_q &= Q(policy_agent_info__referral_id=str(referral_id))

    base_qs = PolicyDocument.objects.filter(filters_q).order_by('-id')
    filters = get_common_filters(request)
    filtered = apply_policy_filters(base_qs, filters)

    # filtered = []
    # for obj in base_qs:
    #     raw = obj.extracted_text
    #     data = {}
        
    #     if isinstance(raw, str):
    #         try:
    #             data = json.loads(raw)
    #         except json.JSONDecodeError:
    #             continue
    #     elif isinstance(raw, dict):
    #         data = raw
    
    #     if not data:
    #         continue

    #     if filters['policy_number'] and filters['policy_number'] not in data.get('policy_number', '').lower():
    #         continue
    #     if filters['vehicle_number'] and filters['vehicle_number'] not in data.get('vehicle_number', '').lower():
    #         continue
    #     if filters['engine_number'] and filters['engine_number'] not in get_nested(data, ['vehicle_details', 'engine_number']).lower():
    #         continue
    #     if filters['chassis_number'] and filters['chassis_number'] not in get_nested(data, ['vehicle_details', 'chassis_number']).lower():
    #         continue
    #     if filters['vehicle_type'] and filters['vehicle_type'] not in get_nested(data, ['vehicle_details', 'vehicle_type']).lower():
    #         continue
    #     if filters['policy_holder_name'] and filters['policy_holder_name'] not in data.get('insured_name', '').lower():
    #         continue
    #     if filters['mobile_number'] and filters['mobile_number'] not in data.get('contact_information', {}).get('phone_number', '').lower():
    #         continue
    #     if filters['insurance_provider'] and filters['insurance_provider'] not in data.get('insurance_company', '').lower():
    #         continue   

    #     obj.json_data = data    # attach parsed dict for the template
    #     obj.policy_infos = obj.policy_info.first()
    #     obj.policy_vehicle_infos = obj.policy_vehicle_info.first()
    #     obj.policy_agent_infos = obj.policy_agent_info.first()
    #     obj.policy_franchise_infos = obj.policy_franchise_info.first()
    #     obj.policy_insurer_infos = obj.policy_insurer_info.first()
    #     filtered.append(obj)

    if role_id != 1 and request.user.department_id != "5" and request.user.department_id != "3" and request.user.department_id != "2":
        policy_count = PolicyDocument.objects.filter(status=6, rm_id=user_id).count()
    else:
        policy_count = PolicyDocument.objects.filter(status=6).count()


    count_qs = PolicyDocument.objects.all()

    status_counts = count_qs.values('operator_verification_status').annotate(count=Count('operator_verification_status'))

    pendingOperator = verifiedOperator = not_verifiedOperator = 0

    # Map status values to named variables
    for entry in status_counts:
        status = entry['operator_verification_status']
        count = entry['count']
        if status == '0':
            pendingOperator = count
        elif status == '1':
            verifiedOperator = count
        elif status == '2':
            not_verifiedOperator = count


    # Pagination
    per_page = request.GET.get('per_page', 10)
    try:
        per_page = int(per_page)
    except ValueError:
        per_page = 10

    paginator = Paginator(filtered, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    branches = Branch.objects.all().order_by('branch_name')
    referrals = Referral.objects.all().order_by('name')
    bqpList = BqpMaster.objects.all().order_by('bqp_fname')
    partners = Partner.objects.all().order_by('name')

    return render(request, 'policy/index.html', {
        "page_obj": page_obj,
        "policy_count": policy_count,
        "branches": branches,
        "referrals": referrals,
        "bqpList": bqpList,
        'pendingOperator': pendingOperator,
        'verifiedOperator': verifiedOperator,
        'not_verifiedOperator': not_verifiedOperator,
        "partners": partners,
        "per_page": per_page,
        'filters': {k: request.GET.get(k,'') for k in filters}
    })

from django.db import IntegrityError

def deletePolicy(request, id):
    if not request.user.is_authenticated:
        return redirect('login')

    policy = get_object_or_404(PolicyDocument, id=id)

    try:
        # Delete all ExtractedFile entries related to this policy
        ExtractedFile.objects.filter(policy=policy).delete()
        
        # Delete all SingleUploadFile entries related to this policy
        SingleUploadFile.objects.filter(policy=policy).delete()

        # Delete the policy itself
        policy.delete()

        messages.success(request, "Policy and related files deleted successfully.")
    except IntegrityError as e:
        messages.error(request, f"Failed to delete policy due to a database integrity issue: {str(e)}")
    except Exception as e:
        messages.error(request, f"Failed to delete policy: {str(e)}")

    return redirect('policy-data')  # Change this if your view name is different

def viewSinglePolicyLog(request):
    if not request.user.is_authenticated and request.user.is_active != 1:
        messages.error(request,'Please Login First')
        
    log_files = SingleUploadFile.objects.all()
    
    non_failed_files = log_files.filter(is_failed = False)
    statuses = Counter(file.status for file in non_failed_files)
    # Ensure all statuses are included in the count, even if they're 0
    status_counts = {
        0: statuses.get(0, 0),
        1: statuses.get(1, 0),
        2: statuses.get(2, 0),
        3: statuses.get(3, 0),
        4: statuses.get(4, 0),
        5: statuses.get(5, 0),
        6: statuses.get(6, 0),
        7: statuses.get(7, 0),
    }

    failed_files_count = log_files.filter(is_failed=True).count()
    
    return render(request,'policy/single-policy-log.html',{
        "log_files":log_files,
        "total_files":len(log_files),
        "failed_files":failed_files_count,
        "status_counts":status_counts
    })
    
    
def get_filter_conditions(filters):
    """
    Generate Q object conditions and post-filter lambdas for fields stored in extracted_text JSON.
    """
    db_filters = Q()
    json_filters = []

    for key, val in filters.items():
        if not val:
            continue
        val = val.strip().lower()
        
        if key in ['policy_number', 'vehicle_number', 'policy_type', 'vehicle_type',
                   'policy_holder_name', 'insurance_provider']:
            field_map = {
                'policy_number': 'policy_number__icontains',
                'vehicle_number': 'vehicle_number__icontains',
                'policy_type': 'policy_type__iexact',
                'vehicle_type': 'vehicle_type__iexact',
                'policy_holder_name': 'holder_name__icontains',
                'insurance_provider': 'insurance_provider__icontains',
            }
            db_filters &= Q(**{field_map[key]: val})

        elif key in ['insurance_company', 'mobile_number', 'engine_number', 'chassis_number', 'fuel_type']:
            json_filters.append(lambda data, k=key, v=val: v in data.get(k, '').lower())

        
        elif key == 'gvw_from':
            try:
                val = int(val)
                json_filters.append(lambda data, v=val: int(data.get('cubic_capacity', '0')) >= v)
            except ValueError:
                continue

        elif key == 'gvw_to':
            try:
                val = int(val)
                json_filters.append(lambda data, v=val: int(data.get('cubic_capacity', '0')) <= v)
            except ValueError:
                continue

        elif key in ['manufacturing_year_from', 'manufacturing_year_to']:
            try:
                year = int(val)
                if key.endswith('from'):
                    json_filters.append(lambda data, y=year: int(data.get('manufacturing_year', '0')) >= y)
                else:
                    json_filters.append(lambda data, y=year: int(data.get('manufacturing_year', '0')) <= y)
            except ValueError:
                continue

        elif key == 'start_date':
            try:
                dt = datetime.strptime(val, '%Y-%m-%d')  # No .date() here
                db_filters &= Q(created_at__gte=dt)
            except ValueError:
                continue

        elif key == 'end_date':
            try:
                dt = datetime.strptime(val, '%Y-%m-%d') + timedelta(days=1)  # Include full end date
                db_filters &= Q(created_at__lt=dt)
            except ValueError:
                continue

    return db_filters, json_filters


def apply_policy_filters(queryset, filters):
    db_q, json_conditions = get_filter_conditions(filters)
    filtered_qs = queryset.filter(db_q)

    final_list = []
    for obj in filtered_qs:
        try:
            data = obj.extracted_text if isinstance(obj.extracted_text, dict) else json.loads(obj.extracted_text or '{}')
        except Exception:
            continue

        if all(cond(data) for cond in json_conditions):
            obj.json_data = data
            final_list.append(obj)

    return final_list


def get_common_filters(request):
    return {
        key: request.GET.get(key, '').strip() for key in [
            'policy_number', 'policy_type', 'vehicle_number', 'engine_number', 'chassis_number',
            'vehicle_type', 'policy_holder_name', 'mobile_number',
            'insurance_provider', 'insurance_company', 'start_date',
            'end_date', 'manufacturing_year_from', 'manufacturing_year_to',
            'fuel_type', 'gvw_from', 'gvw_to', 'branch_name', 'referred_by', 'pos_name', 'bqp'
        ]
    }