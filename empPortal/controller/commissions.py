from django.http import HttpResponse
from django.contrib.auth.hashers import make_password
from django.contrib.auth import update_session_auth_hash
from django.shortcuts import render,redirect, get_object_or_404
from django.contrib import messages
from django.template import loader
from ..models import Commission,Users,CommissionHistory
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

from pprint import pprint 

OPENAI_API_KEY = settings.OPENAI_API_KEY

app = FastAPI()


def dictfetchall(cursor):
    "Returns all rows from a cursor as a dict"
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]
from django.db import connection
from django.shortcuts import render, redirect



def commissions(request):
    if request.user.is_authenticated:
        user_id = request.user.id

        if request.user.role_id == 1:  # Admin
            query = """
                SELECT c.*, u.first_name, u.last_name, u.user_gen_id, c.product_id
                FROM commissions c
                LEFT JOIN users u ON c.member_id = u.id
                WHERE u.role_id = 4
                ORDER BY c.id DESC
            """
            count_total_query = """
                SELECT COUNT(*) FROM commissions c
                LEFT JOIN users u ON c.member_id = u.id
                WHERE u.role_id = 4
            """
            count_active_query = """
                SELECT COUNT(*) FROM commissions c
                LEFT JOIN users u ON c.member_id = u.id
                WHERE u.role_id = 4 AND c.active = 1
            """
            count_inactive_query = """
                SELECT COUNT(*) FROM commissions c
                LEFT JOIN users u ON c.member_id = u.id
                WHERE u.role_id = 4 AND c.active = 0
            """
            params = []
            count_params = []
        else:  # Regular member
            query = """
                SELECT c.*, u.first_name, u.last_name, c.product_id
                FROM commissions c
                LEFT JOIN users u ON c.member_id = u.id
                WHERE c.member_id = %s
                ORDER BY c.id DESC
            """
            count_total_query = "SELECT COUNT(*) FROM commissions WHERE member_id = %s"
            count_active_query = "SELECT COUNT(*) FROM commissions WHERE member_id = %s AND active = 1"
            count_inactive_query = "SELECT COUNT(*) FROM commissions WHERE member_id = %s AND active = 0"
            params = [user_id]
            count_params = [user_id]

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            commissions_list = dictfetchall(cursor)

            # Fetch counts
            cursor.execute(count_total_query, count_params)
            total_count = cursor.fetchone()[0]

            cursor.execute(count_active_query, count_params)
            active_count = cursor.fetchone()[0]

            cursor.execute(count_inactive_query, count_params)
            inactive_count = cursor.fetchone()[0]

        # Define available products
        products = [
            {'id': 1, 'name': 'Motor'},
            {'id': 2, 'name': 'Health'},
            {'id': 3, 'name': 'Term'},
        ]
        product_dict = {product['id']: product['name'] for product in products}

        for commission in commissions_list:
            product_id = commission.get('product_id')
            if product_id is not None:
                commission['product_name'] = product_dict.get(int(product_id), 'Unknown')
            else:
                commission['product_name'] = 'Unknown'

        context = {
            'commissions': commissions_list,
            'total_count': total_count,
            'active_count': active_count,
            'inactive_count': inactive_count,
        }

        return render(request, 'commissions/commissions.html', context)
    else:
        return redirect('login')



    
def create(request):
    if request.user.is_authenticated:

        products = [
            {'id': 1, 'name': 'Motor'},
            {'id': 2, 'name': 'Health'},
            {'id': 3, 'name': 'Term'},
        ]
        
        if request.user.role_id == 1:
            members = Users.objects.filter(role_id=4, activation_status='1')
        else:
            members = Users.objects.none()
    
        return render(request, 'commissions/create.html', {'products': products, 'members': members})
    else:
        return redirect('login')
   
def store(request):
    if not request.user.is_authenticated:
        return redirect('login')

    if request.method == "POST":
        member_id = request.POST.get('member', '').strip()
        product_id = request.POST.get('product', '').strip()
        tp_percentage = request.POST.get('tp_percentage', '').strip()
        od_percentage = request.POST.get('od_percentage', '').strip()
        net_percentage = request.POST.get('net_percentage', '').strip()

        # Validations
        if not member_id:
            messages.error(request, "Member is required.")
        if not product_id:
            messages.error(request, "Product is required.")
        if not tp_percentage or not tp_percentage.replace('.', '', 1).isdigit():
            messages.error(request, "Valid TP percentage is required.")
        if not od_percentage or not od_percentage.replace('.', '', 1).isdigit():
            messages.error(request, "Valid OD percentage is required.")
        if not net_percentage or not net_percentage.replace('.', '', 1).isdigit():
            messages.error(request, "Valid Net percentage is required.")

        # Check if this sub-broker already has a commission for the selected insurer
        if Commission.objects.filter(member_id=member_id, product_id=product_id).exists():
            messages.error(request, "You already have a commission for this member & product.")

        # If any errors, redirect back to the 'add-commission' page
        if messages.get_messages(request):
            return redirect('add-commission')

        # Save to database
        new_commission = Commission.objects.create(
            product_id=product_id,
            member_id=member_id,
            tp_percentage=float(tp_percentage),
            od_percentage=float(od_percentage),
            net_percentage=float(net_percentage),
            created_by=request.user.id
        )

        CommissionHistory.objects.create(
            commission_id=new_commission.id,  # ✅ Use the instance's ID
            member_id=member_id,
            product_id=product_id,
            tp_percentage=tp_percentage,
            od_percentage=od_percentage,
            net_percentage=net_percentage,
            created_by=request.user.id
        )



        messages.success(request, "Commission added successfully.")
        return redirect('commissions')

    else:
        messages.error(request, "Invalid request.")
        return redirect('add-commission')
    
def update_commission(request):
    if not request.user.is_authenticated:
        return redirect("login")

    if request.method == "POST":
        commission_id   = request.POST.get("commission_id", "").strip()
        member_id       = request.POST.get("member_id", "").strip()
        product_id      = request.POST.get("product", "").strip()
        tp_percentage   = request.POST.get("tp_percentage", "").strip()
        od_percentage   = request.POST.get("od_percentage", "").strip()
        net_percentage  = request.POST.get("net_percentage", "").strip()

        # Ensure at least commission_id or member_id is provided
        if not commission_id and not member_id:
            messages.error(request, "Either Commission ID or Member ID is required.")
            return redirect("members")

        # Validate required fields
        if not all([product_id, tp_percentage, od_percentage, net_percentage]):
            messages.error(request, "Product and percentage fields are required.")
            return redirect("members")

        # Validate numeric inputs
        try:
            tp_percentage = float(tp_percentage)
            od_percentage = float(od_percentage)
            net_percentage = float(net_percentage)
        except ValueError:
            messages.error(request, "Percentage values must be numeric.")
            return redirect("members")

        # Fetch or create a commission record
        if commission_id.isdigit():  # Update an existing record
            commission = get_object_or_404(Commission, id=int(commission_id))
            action_message = "Commission updated successfully."
        elif member_id.isdigit():  # Create a new record if only member_id is provided
            if Commission.objects.filter(member_id=member_id, product_id=product_id).exists():
                messages.error(request, "A commission for this member & product already exists.")
                return redirect('member-view', user_id=member_id)

            commission = Commission(member_id=member_id)
            action_message = "Commission added successfully."
        else:
            messages.error(request, "Invalid Commission ID or Member ID.")
            return redirect("members")

        # Update or create commission
        commission.product_id = product_id
        commission.tp_percentage = tp_percentage
        commission.od_percentage = od_percentage
        commission.net_percentage = net_percentage
        commission.save()

        # Log the commission update in history
        CommissionHistory.objects.create(
            commission_id=commission.id,
            member_id=commission.member_id,
            product_id=product_id,
            tp_percentage=tp_percentage,
            od_percentage=od_percentage,
            net_percentage=net_percentage,
            created_by=request.user.id
        )

        messages.success(request, action_message)

        user_details = Users.objects.get(id=commission.member_id)

        # Redirect based on role_id
        if user_details.role_id == 1:
            return redirect("my-account")
        else:
            return redirect("member-view", user_id=commission.member_id)

    messages.error(request, "Invalid request method.")
    return redirect("members")
