from django.http import HttpResponse
from django.contrib.auth.hashers import make_password
from django.contrib.auth import update_session_auth_hash
from django.shortcuts import render,redirect, get_object_or_404
from django.contrib import messages
from django.template import loader
from ..models import Commission,Users, DocumentUpload, Branch
from empPortal.model import BankDetails
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
import os
import pdfkit
from django.template.loader import render_to_string
from pprint import pprint 

OPENAI_API_KEY = settings.OPENAI_API_KEY

app = FastAPI()


def dictfetchall(cursor):
    "Returns all rows from a cursor as a dict"
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

def index(request):
    if request.user.is_authenticated:
        user_details = Users.objects.get(id=request.user.id)  # Fetching the user's details

        
        
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
            
        return render(request, 'help-and-support/index.html', {
            'user_details': user_details,
            'manager_list': manager_list,
            'rm_list': rm_list,
            'tl_list': tl_list,
            'branches': branches,
            'rm_details': rm,
            'tl_details': tl,
            'branch': branch,
            'manager_details': manager,
            'branch': branch,
            'branch_manager': manager,
        })
    else:
        return redirect('login')
