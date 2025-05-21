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
        return render(request, 'sell/motor/index.html')
    else:
        return redirect('login')

def createMotorInsurance(request):
    if request.user.is_authenticated:
        return render(request, 'sell/motor/motor-insurance.html')
    else:
        return redirect('login')
    
def createMotorDetails(request):
    if request.user.is_authenticated:
        return render(request, 'sell/motor/motor-details.html')
    else:
        return redirect('login')
    
def createMotorQuote(request):
    if request.user.is_authenticated:
        return render(request, 'sell/motor/motor-quote.html')
    else:
        return redirect('login')
    
def createMotorProposalBasicDetails(request):
    if request.user.is_authenticated:
        return render(request, 'sell/motor/motor-proposal-basic-details.html')
    else:
        return redirect('login')
    
def createMotorProposalNomineeDetails(request):
    if request.user.is_authenticated:
        return render(request, 'sell/motor/motor-proposal-nominee-details.html')
    else:
        return redirect('login')
    
def createMotorProposalAddressDetails(request):
    if request.user.is_authenticated:
        return render(request, 'sell/motor/motor-proposal-address-details.html')
    else:
        return redirect('login')
    
def createMotorProposalVehicleDetails(request):
    if request.user.is_authenticated:
        return render(request, 'sell/motor/motor-proposal-vehicle-details.html')
    else:
        return redirect('login')
    
def createMotorProposalSummary(request):
    if request.user.is_authenticated:
        return render(request, 'sell/motor/motor-proposal-summary.html')
    else:
        return redirect('login')

def create4wMotorInsurance(request):
    if request.user.is_authenticated:
        return render(request, 'sell/motor/4w/motor-insurance.html')
    else:
        return redirect('login')

def create4wMotorDetails(request):
    if request.user.is_authenticated:
        return render(request, 'sell/motor/4w/motor-details.html')
    else:
        return redirect('login')

def create4wMotorQuote(request):
    if request.user.is_authenticated:
        return render(request, 'sell/motor/4w/motor-quote.html')
    else:
        return redirect('login')

def create4wMotorProposalBasicDetails(request):
    if request.user.is_authenticated:
        return render(request, 'sell/motor/4w/motor-proposal-basic-details.html')
    else:
        return redirect('login')

def create4wMotorProposalNomineeDetails(request):
    if request.user.is_authenticated:
        return render(request, 'sell/motor/4w/motor-proposal-nominee-details.html')
    else:
        return redirect('login')

def create4wMotorProposalAddressDetails(request):
    if request.user.is_authenticated:
        return render(request, 'sell/motor/4w/motor-proposal-address-details.html')
    else:
        return redirect('login')

def create4wMotorProposalVehicleDetails(request):
    if request.user.is_authenticated:
        return render(request, 'sell/motor/4w/motor-proposal-vehicle-details.html')
    else:
        return redirect('login')

def create4wMotorProposalSummary(request):
    if request.user.is_authenticated:
        return render(request, 'sell/motor/4w/motor-proposal-summary.html')
    else:
        return redirect('login')
