import fitz
import json
import logging
import openai
import os
import pdfkit
import re
import requests
import time
import zipfile
from django.utils.timezone import localtime

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash, authenticate, login ,logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.core.cache import cache
from django.core.files.storage import FileSystemStorage
from django.core.mail import send_mail, EmailMessage
from django.core.paginator import Paginator
from django.db import connection
from django.db.models import Q, Value
from django.db.models.functions import Concat
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest
from django.shortcuts import render,redirect, get_object_or_404

from ..models import Users
from empPortal.model.Dispositions import SubDisposition

logger = logging.getLogger(__name__)

def get_sub_disposition_list(request):
    if request.method != 'POST':
        return HttpResponseBadRequest("Invalid request method.")

    disposition_id = request.POST.get('disposition_id')
    if not disposition_id:
        return JsonResponse({'error': 'Disposition ID is required'}, status=400)

    sub_disposition_list = SubDisposition.objects.filter(
        sub_disp_fk_disp_id=disposition_id,
        sub_disp_is_active=True
    ).values('sub_disp_id', 'sub_disp_ref_id', 'sub_disp_name')

    return JsonResponse({'sub_disposition_list': list(sub_disposition_list)})
