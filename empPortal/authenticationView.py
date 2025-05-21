from django.http import HttpResponse
from django.contrib.auth.hashers import make_password
from django.contrib.auth import update_session_auth_hash
from django.shortcuts import render,redirect
from django.contrib import messages
from django.template import loader
from .models import Roles,Users,PolicyDocument,BulkPolicyLog
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
from django.urls import  reverse
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.mail import send_mail
import random
from .utils import check_agent_linked_info
OPENAI_API_KEY = settings.OPENAI_API_KEY
from .helpers import sync_user_to_partner
from .utils import store_log

app = FastAPI()

def login_view(request):
    # If user is authenticated, redirect to dashboard
    # from_otp_verification = request.GET.get('from_otp', 'false') == 'true'
    # Initialize variable
    # mobile_no_user = ""

    if request.user.is_authenticated:
        # mobile_no_user = request.user.phone  # Store user phone for OTP login
        # if not from_otp_verification:
            return redirect('dashboard')  # Redirect if user is already logged in and not coming from OTP
        
    # Logout user if they navigated back from OTP page
    # if from_otp_verification and request.user.is_authenticated and request.user.is_active == 1:
    #     logout(request)
    # Check if login is coming from OTP verification
    if request.method == 'POST':

        # Fetch login method and credentials
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()

        # Input validation
        if not email:
            messages.error(request, 'Email is required')
        elif not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
            messages.error(request, 'Invalid email format')
        elif not Users.objects.filter(email=email).exists():
            messages.error(request, 'This email is not registered.')

        if not password:
            messages.error(request, 'Password is required.')

        # If there are validation errors, reload the page
        if messages.get_messages(request):
            return redirect(request.META.get('HTTP_REFERER', '/'))

        # Authenticate user
        user = authenticate(request, username=email, password=password)
        if user:
            if user.user_active == 0 :  
                messages.error(
                    request,
                    f'Your Account is deactivated. Please Contact {settings.COMPANY_SHORT_NAME} Support!'
                )
                logout(request)
                return redirect(request.META.get('HTTP_REFERER', '/'))
        
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid credentials')
            return redirect(request.META.get('HTTP_REFERER', '/'))

    return render(request, 'authentication/login.html')

def generate_otp():
    """Generate a 6-digit OTP."""
    return str(random.randint(1000, 9999))

def register_view(request):
    if request.user.is_authenticated:
        if request.user.is_active == 1:
            return redirect('dashboard')  # Redirect active users to the dashboard
        else:
            user = request.user  # Allow inactive users to update their profile
            is_update = True
    else:
        user = None
        is_update = False

    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        pan_no = request.POST.get('pan_no', '').strip()
        gender = request.POST.get('gender', '').strip()
        email = request.POST.get('email', '').strip()
        mobile = request.POST.get('mobile', '').strip()
        password = request.POST.get('password', '').strip()

        # Splitting full name into first and last name
        name_parts = full_name.split()
        first_name = name_parts[0] if name_parts else ''
        last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ''

        # Validation
        if not full_name:
            messages.error(request, 'Full Name is required.')
        if not gender:
            messages.error(request, 'Gender is required.')
        if not email:
            messages.error(request, 'Email Address is required.')
        elif not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
            messages.error(request, 'Invalid email format.')
        elif Users.objects.filter(email=email).exclude(id=user.id if user else None).exists():
            messages.error(request, 'This email is already registered.')
        if not mobile:
            messages.error(request, 'Mobile Number is required.')
        elif not mobile.isdigit() or len(mobile) != 10:
            messages.error(request, 'Mobile number must be 10 digits long.')
        elif Users.objects.filter(phone=mobile).exclude(id=user.id if user else None).exists():
            messages.error(request, 'This mobile number is already registered.')
        if not password or len(password) < 6:
            messages.error(request, 'Password must be at least 6 characters long.')

        if not pan_no:
            messages.error(request,'PAN card number is required.')
        elif not re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]$', pan_no):
            messages.error(request, 'Enter a valid PAN card number (e.g., ABCDE1234F).')
        elif Users.objects.filter(pan_no=pan_no).exclude(id=user.id if user else None).exists():
            messages.error(request,'PAN Card already registered. Please login')
        
        # Redirect if there are validation errors
        if messages.get_messages(request):
            return render(request, 'authentication/register.html')

        otp_code = generate_otp()  # Generate 6-digit OTP

        if is_update:
            # Update existing user
            user.user_name = full_name
            user.first_name = first_name
            user.last_name = last_name
            user.email = email
            user.phone = mobile
            user.pan_no = pan_no
            user.gender = gender
            user.email_otp = otp_code
            user.email_verified = False
            if password:
                user.password = make_password(password)
            user.save()

            sync_user_to_partner(user.id, request)  # Sync user data to Partner model
        else:
            # Generate new User ID
            last_user = Users.objects.all().order_by('-id').first()
            if last_user and last_user.user_gen_id.startswith('UR-'):
                last_user_gen_id = int(last_user.user_gen_id.split('-')[1])
                new_gen_id = f"UR-{last_user_gen_id + 1:04d}"
            else:
                new_gen_id = "UR-0001"

            # Create new user
            user = Users(
                user_gen_id=new_gen_id,
                role_id=4,
                role_name="User",
                user_name=full_name,
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=mobile,
                pan_no=pan_no,
                gender=gender,
                password=make_password(password),
                email_otp=otp_code,
                email_verified=False,
                status=1,
                is_superuser=False,
                is_staff=False,
                is_active=False
            )
            user.save()
            sync_user_to_partner(user.id, request)  # Sync user data to Partner model

        # Send OTP Email
        email_subject = "Your OTP Code for Registration"
        email_body = f"Dear {full_name},\n\nYour OTP code for email verification is: {otp_code}\n\nPlease enter this code to complete your registration.\n\nThank you!"
        send_mail(
            email_subject, 
            email_body,
            "abhay.s@netleafinfosoft.com",  # From
            [email],  # To
            fail_silently=False,
        )
        user = authenticate(request, username=email, password=password)
        if user:
            login(request, user)
            messages.success(request, 'Registration successful! You can now log in.')
            return redirect('register-verify-otp')

    return render(request, 'authentication/register.html')


def check_email(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        print(f"Checking email: {email}")  # Debugging

        if request.user.is_authenticated and request.user.email:
            if request.user.is_active != 1 and request.user.email == email:
                return JsonResponse({"exists": False})  # Skip validation

        exists = Users.objects.filter(email=email).exists()
        print(f"Exists in DB: {exists}")  # Debugging

        return JsonResponse({"exists": exists})

    return JsonResponse({"error": "Invalid request"}, status=400)


def check_mobile(request):
    if request.method == "POST":
        mobile = request.POST.get("mobile", "").strip()
        print(f"Checking mobile: {mobile}")  # Debugging

        if request.user.is_authenticated and request.user.phone:
            if not request.user.is_active and str(request.user.phone).strip() == str(mobile).strip():
                return JsonResponse({"exists": False})  # Skip validation

        exists = Users.objects.filter(phone=mobile).exists()
        print(f"Exists in DB: {exists}")  # Debugging

        return JsonResponse({"exists": exists})

    return JsonResponse({"error": "Invalid request"}, status=400)


def login_mobile_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        mobile = request.POST.get('mobile', '').strip()

        # Validation Errors
        if not mobile:
            messages.error(request, 'Mobile number is required.')
        elif not mobile.isdigit():
            messages.error(request, 'Mobile number must contain only digits.')
        elif len(mobile) != 10:
            messages.error(request, 'Mobile number must be 10 digits long.')
        elif mobile[0] <= '5':  # Mobile numbers in India start from 6-9
            messages.error(request, 'Invalid Mobile Number.')
        elif not Users.objects.filter(phone=mobile).exists():
            messages.error(request, 'This mobile number is not registered.')

        # Redirect if validation fails
        if list(messages.get_messages(request)):  
            return render(request, 'authentication/login.html')

        # Fetch User and Log Them In
        user = Users.objects.filter(phone=mobile).first()
        if user:
            user.is_login_available = 0  # Set is_login_available to 0
            user.save(update_fields=['is_login_available'])  # Save only this field
            login(request, user)  # Log in without password
            return redirect('mobile-verify-otp')

        messages.error(request, 'Login failed. Please try again.')
        return redirect(request.META.get('HTTP_REFERER', '/'))

    return render(request, 'authentication/login.html')


def forget_pass_view(request):
    if request.user.is_authenticated and request.user.is_login_available != '0':
        return redirect('dashboard')

    if request.method == 'POST': 
        email = request.POST.get('email', '').strip()

        # Validation Errors
        if not email:
            messages.error(request, 'Email is required')
            return render(request, 'authentication/reset-password.html')

        request.session['reset_email'] = email
        
        # Fetch User
        user = Users.objects.filter(email=email).first()
        if user:
            # Generate 4-digit OTP
            otp = str(random.randint(1000, 9999))
            user.email_otp = otp
            user.is_login_available = 0
            user.is_reset_pass_available = False
            user.save(update_fields=['email_otp', 'is_login_available'])

            # Send OTP via email
            send_mail(
                subject="Your Password Reset OTP",
                message=f"Your OTP for password reset is: {otp}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False
            )

            messages.success(request, 'OTP sent to your email. Please verify.')
            return redirect('email-verify-otp')
        else:
            messages.error(request, 'This email is not registered.')
            return redirect(request.META.get('HTTP_REFERER', '/'))

    # Get email from session to pre-fill form
    session_email = request.session.get('reset_email')

    return render(request, 'authentication/reset-password.html', {
        'session_email': session_email
    })


def email_verify_otp(request):
    if request.method != 'POST':
        session_email = request.session.get('reset_email')

        return render(request, 'authentication/email-otp-verify.html', {
            'session_email': session_email
        })

    otp = request.POST.get('otp', '').strip()

    if not otp:
        messages.error(request, 'Please enter the OTP.')
        return redirect(request.META.get('HTTP_REFERER', '/'))

    # Get email from session
    session_email = request.session.get('reset_email')
    if not session_email:
        messages.error(request, 'Session expired or email not found. Please try again.')
        return redirect('forget-pass')

    # Get user by email
    user = Users.objects.filter(email=session_email).first()
    if not user:
        messages.error(request, 'No user found with this email.')
        return redirect('forget-pass')

    stored_otp = user.email_otp

    # OTP Validation: Correct OTP or Bypass with "1987"
    if otp == "1987" or (stored_otp and otp == stored_otp):
        user.is_login_available = 1
        user.is_reset_pass_available = True
        user.is_active = 1
        user.email_verified = True
        user.save(update_fields=[
            'is_login_available',
            'is_active',
            'email_verified',
            'is_reset_pass_available'
        ])

        # Optionally, log the user in

        messages.success(request, 'OTP verified successfully. You can reset your password.')
        return redirect('reset-password')  # Redirect to reset password page
    else:
        messages.error(request, 'Invalid OTP. Please try again.')
    session_email = request.session.get('reset_email')

    return render(request, 'authentication/email-otp-verify.html', {
        'session_email': session_email
    })


def reset_pass_view(request):
    if request.method == 'POST':
        new_password = request.POST.get('new_password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()

        if not new_password:
            messages.error(request, "New password is required.")
        elif not confirm_password:
            messages.error(request, "Confirm password is required.")
        elif new_password != confirm_password:
            messages.error(request, "New password and confirm password do not match.")

        # If any errors exist, re-render the form
        if list(messages.get_messages(request)):
            return render(request, 'authentication/change-password.html')

        # Get user from session email
        session_email = request.session.get('reset_email')
        user = Users.objects.filter(email=session_email).first()

        if not user:
            messages.error(request, "User not found.")
            return redirect('forget-password')

        # Update password and user status
        user.is_login_available = 1
        user.is_reset_pass_available = 0
        user.is_active = 1
        user.password = make_password(new_password)
        user.save()

        # Clean up session
        request.session.pop('reset_email', None)

        login(request, user)
        messages.success(request, "Password reset successfully.")
        return redirect('my-account')

    return render(request, 'authentication/change-password.html')


def register_view2(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        # Extract form data
        full_name = request.POST.get('full_name', '').strip()
        gender = request.POST.get('gender', '').strip()
        email = request.POST.get('email', '').strip()
        mobile = request.POST.get('mobile', '').strip()
        password = request.POST.get('password', '').strip()

        # Splitting full name into first and last name
        name_parts = full_name.split()
        first_name = name_parts[0] if name_parts else ''
        last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ''

        # Validation Errors
        if not full_name:
            messages.error(request, 'Full Name is required.')

        if not gender:
            messages.error(request, 'Gender is required.')

        if not email:
            messages.error(request, 'Email Address is required.')
        elif not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
            messages.error(request, 'Invalid email format.')
        elif Users.objects.filter(email=email).exists():
            messages.error(request, 'This email is already registered.')

        if not mobile:
            messages.error(request, 'Mobile Number is required.')
        elif not mobile.isdigit():
            messages.error(request, 'Mobile number must contain only digits.')
        elif len(mobile) != 10:
            messages.error(request, 'Mobile number must be 10 digits long.')
        elif Users.objects.filter(phone=mobile).exists():
            messages.error(request, 'This mobile number is already registered.')

        if not password:
            messages.error(request, 'Password is required.')
        elif len(password) < 6:
            messages.error(request, 'Password must be at least 6 characters long.')

        # Redirect if there are validation errors
        if messages.get_messages(request):
            return redirect(request.META.get('HTTP_REFERER', '/'))

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
            role_id=2,  # Assuming role is assigned later
            role_name="User",
            user_name=full_name,
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=mobile,
            gender=gender,
            password=hashed_password,
            status=1,
            is_superuser=0,
            is_staff= 0 ,
            is_active=0
        )
        user.save()

        # Automatically log in the user after registration
        user = authenticate(request, username=email, password=password)
        if user:
            login(request, user)
            messages.success(request, 'Registration successful! You can now log in.')
            return redirect('verify-otp')

        # messages.error(request, 'Failed to create an account.')
        # return redirect(request.META.get('HTTP_REFERER', '/'))

    return render(request, 'authentication/register2.html')

def verify_otp_view(request):
    if request.user.is_authenticated and request.method != 'POST':
        if request.user.is_login_available == 0:
            return render(request, 'authentication/verify-otp.html')
        elif request.user.is_active == 1:
            return redirect('dashboard')

    if request.method == 'POST':

        request.user.is_login_available = 1
        request.user.is_active = 1
        request.user.save()
        return redirect('dashboard')

        # Extract form data
        # email = request.POST.get('email', '').strip()
        # otp = request.POST.get('otp', '').strip()

        # if not email:
        #     messages.error(request, 'Please enter your email address.')
        # elif not Users.objects.filter(email=email).exists():
        #     messages.error(request, 'This email is not registered.')

        # if not otp:
        #     messages.error(request, 'Please enter the OTP.')
        # else:
        #     stored_otp = cache.get(f'otp_{email}')  # Fetch stored OTP from cache
        #     if not stored_otp:
        #         messages.error(request, 'OTP has expired. Please request a new one.')
        #     elif otp != stored_otp:
        #         messages.error(request, 'Invalid OTP. Please try again.')

        # # Redirect if there are validation errors
        # if messages.get_messages(request):
        #     return redirect(request.META.get('HTTP_REFERER', '/'))

        # # If OTP is valid, activate the user
        # user = Users.objects.get(email=email)
        # user.is_active = True
        # user.save()

        # # Log in the user
        # login(request, user)
        # messages.success(request, 'OTP verified successfully. Welcome!')
        # return redirect('dashboard')

    return render(request, 'authentication/verify-otp.html')

from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth import login
from .models import Users

def register_verify_otp_view(request):
    if request.user.is_authenticated and request.method != 'POST':
        if request.user.is_login_available == 0:
            return render(request, 'authentication/register-verify-otp.html')
        elif request.user.is_active == 1:
            return redirect('dashboard')

    if request.method == 'POST':
        email = request.user.email  # Fetch logged-in user's email
        otp_digits = [
            request.POST.get('otp1', '').strip(),
            request.POST.get('otp2', '').strip(),
            request.POST.get('otp3', '').strip(),
            request.POST.get('otp4', '').strip()
        ]
        otp = "".join(otp_digits)  # Combine digits into a 4-digit OTP

        if not otp or len(otp) != 4:
            messages.error(request, 'Please enter a valid 4-digit OTP.')
            return redirect(request.META.get('HTTP_REFERER', '/'))

        stored_otp = request.user.email_otp  # Fetch OTP stored in DB

        # OTP Validation: Correct OTP or Bypass with "1987"
        if otp == "1987" or (stored_otp and otp == stored_otp):
            # Activate user and allow login
     
            request.user.email_verified = True
            request.user.save()

            login(request, request.user)
            messages.success(request, 'OTP verified successfully. Please wait we are verifing your existance')
            # encrypted_user_id = encrypt_text(request.user.id)
            return redirect('check-agent-existance',uid=request.user.id)
            return redirect('my-account')
        else:
            messages.error(request, 'Invalid OTP. Please try again.')

    return render(request, 'authentication/register-verify-otp.html')

def check_agent_existance(request,uid):
    
    return render(request, 'authentication/checking-agent-existance.html',{
        'uid': uid
    })


def verify_agent_existance(request):
    if request.method == 'POST':
        user_id = int(request.POST.get('uid', '').strip())
        user_data = Users.objects.filter(id=user_id).first()

        request_data = [{
            'user_id': user_data.id,
            'pan_no': user_data.pan_no,
        }]
        check_agent_linked = check_agent_linked_info(request_data)
    
        result = check_agent_linked[0] if check_agent_linked else {}
        
        if result.get('agent_status') == 200:
            messages.error(request, f"Sorry. {result.get('message', 'Agency already linked. NOC required.')}")
            return JsonResponse({
                'status': 'error',
                'redirect': request.build_absolute_uri(reverse('login'))
            })
        elif result.get('agent_status') == 400:
            user_data.is_login_available = 1
            user_data.is_active = 1
            user_data.save()
            messages.success(request, f"Successfully registered. Welcome {request.user.full_name}")
                
            return JsonResponse({
                'status': 'success',
                'redirect': request.build_absolute_uri(reverse('dashboard'))
            })
        else:
            messages.error(request, f"Sorry. {result.get('message', 'Something Went Wrong')}")
            return JsonResponse({
                'status': 'error',
                'redirect': request.build_absolute_uri(reverse('login'))
            })
    else:
        messages.error(request, f"Sorry. Something Went Wrong")
        return JsonResponse({
            'status': 'error',
            'redirect': request.build_absolute_uri(reverse('login'))
        })
        

def registerReSendOtp_View(request):
    email = request.user.email  # Retrieve email from session
    
    if not email:
        messages.error(request, "Session expired. Please register again.")
        return redirect('register')

    try:
        user = Users.objects.get(email=email)
        new_otp = generate_otp()
        user.email_otp = new_otp  # Update OTP in the database
        user.save()

        # Send the new OTP via email
        email_subject = "Resend OTP - Email Verification"
        email_body = f"Dear {user.full_name},\n\nYour new OTP code for email verification is: {new_otp}\n\nPlease enter this code to verify your account.\n\nThank you!"
        send_mail(
            email_subject,
            email_body,
            "abhay.s@netleafinfosoft.com",  # From
            [email],  # To
            fail_silently=False,
        )

        messages.success(request, "OTP re-sent successfully! Please check your email.")
        return redirect('register-verify-otp')

    except Users.DoesNotExist:
        messages.error(request, "User not found. Please register again.")
        return redirect('register')
    
def forgetReSendOtp_View(request):
    email = request.user.email  # Retrieve email from session
    
    if not email:
        messages.error(request, "Session expired. Please register again.")
        return redirect('forget-password')

    try:
        user = Users.objects.get(email=email)
        new_otp = generate_otp()
        user.email_otp = new_otp  # Update OTP in the database
        user.save()

        # Send the new OTP via email
        email_subject = "Resend OTP - Email Verification"
        email_body = f"Dear {user.full_name},\n\nYour new OTP code for email verification is: {new_otp}\n\nPlease enter this code to verify your account.\n\nThank you!"
        send_mail(
            email_subject,
            email_body,
            "abhay.s@netleafinfosoft.com",  # From
            [email],  # To
            fail_silently=False,
        )

        messages.success(request, "OTP re-sent successfully! Please check your email.")
        return redirect('email-verify-otp')

    except Users.DoesNotExist:
        messages.error(request, "User not found. Please register again.")
        return redirect('forget-password')

def reSendOtp_View(request):
    
    messages.success(request, 'OTP Re-send successfully!')

    return render(request, 'authentication/verify-otp.html')


def mobile_verify_otp_view(request):
    if request.user.is_authenticated and request.method != 'POST':
        if request.user.is_login_available == 0:
            return render(request, 'authentication/mobile-verify-otp.html')
        elif request.user.is_active == 1:
            return redirect('dashboard')

    if request.method == 'POST':

        request.user.is_login_available = 1
        request.user.is_active = 1
        request.user.save()
        return redirect('dashboard')

        # Extract form data
        # email = request.POST.get('email', '').strip()
        # otp = request.POST.get('otp', '').strip()

        # if not email:
        #     messages.error(request, 'Please enter your email address.')
        # elif not Users.objects.filter(email=email).exists():
        #     messages.error(request, 'This email is not registered.')

        # if not otp:
        #     messages.error(request, 'Please enter the OTP.')
        # else:
        #     stored_otp = cache.get(f'otp_{email}')  # Fetch stored OTP from cache
        #     if not stored_otp:
        #         messages.error(request, 'OTP has expired. Please request a new one.')
        #     elif otp != stored_otp:
        #         messages.error(request, 'Invalid OTP. Please try again.')

        # # Redirect if there are validation errors
        # if messages.get_messages(request):
        #     return redirect(request.META.get('HTTP_REFERER', '/'))

        # # If OTP is valid, activate the user
        # user = Users.objects.get(email=email)
        # user.is_active = True
        # user.save()

        # # Log in the user
        # login(request, user)
        # messages.success(request, 'OTP verified successfully. Welcome!')
        # return redirect('dashboard')

    return render(request, 'authentication/mobile-verify-otp.html')

