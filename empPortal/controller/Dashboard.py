from django.http import HttpResponse
from django.contrib.auth.hashers import make_password
from django.contrib.auth import update_session_auth_hash
from django.shortcuts import render,redirect
from django.contrib import messages
from django.template import loader
from ..models import Roles,Users, Department,PolicyDocument,BulkPolicyLog, PolicyInfo, Branch, UserFiles,UnprocessedPolicyFiles, Commission, Branch, FileAnalysis, ExtractedFile, ChatGPTLog, AgentPaymentDetails,Leads
from django.contrib.auth import authenticate, login ,logout
from empPortal.model import Quotation
from empPortal.model import Partner

from django.core.files.storage import FileSystemStorage
import re, logging
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
from datetime import datetime
from io import BytesIO
from django.db.models import Q
from ..models import UploadedZip
from django.core.files.base import ContentFile
from ..tasks import process_zip_file
from django_q.tasks import async_task
from django.db.models import Sum
from django.utils import timezone
from django.utils.timezone import now
from empPortal.model import Referral
from urllib.parse import urljoin
from collections import Counter
from django.core.paginator import Paginator
import calendar
from django.db.models.functions import ExtractMonth, ExtractYear


OPENAI_API_KEY = settings.OPENAI_API_KEY
logging.getLogger('faker').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

app = FastAPI()

from django.db.models import Count, Sum, F
from django.db.models.functions import Cast
from django.db.models import FloatField, Sum
from django.db.models import OuterRef, Subquery, Count


from django.utils.timezone import make_naive
from django.db import connection
from datetime import datetime, date
from django.utils.timezone import now



def dashboard(request):
    if not request.user.is_authenticated:
        return redirect('login')
    
    # Get filter params
    date_filter = request.GET.get('date_filter', 'all')
    from_date = request.GET.get('insurer_wise_from_date')
    to_date = request.GET.get('insurer_wise_to_date')
    selected_month = request.GET.get('insurer_wise_summary_month')

    user = request.user

    
    base_qs = PolicyDocument.objects.filter(status=6)

    if request.user.department_id == "1":
        aggregation_qs = base_qs.filter(policy_info__isnull=False, rm_id=request.user.id).distinct()
    else:
        aggregation_qs = base_qs.filter(policy_info__isnull=False).distinct()

    if request.user.role_id == 1:
        # Admin or superuser: show all quotations
        quotation = Quotation.objects.all()
    else:
        # Only show quotations created by the logged-in user
        quotation = Quotation.objects.filter(
            created_by=str(request.user.id)
        )

    # Get the count from the 'quotation' variable
    total_quotation_count = quotation.count()

    # Grouped summary by insurance provider
    provider_summary = (
        aggregation_qs
        .values('insurance_provider')
        .annotate(
            policies_sold=Count('id', distinct=True),
            policy_income=Sum(Cast('policy_premium', output_field=FloatField())),
            total_net_premium=Sum(Cast('policy_info__net_premium', FloatField())),
            total_gross_premium=Sum(Cast('policy_info__gross_premium', FloatField())),
        )
        .order_by('-policy_income', '-policies_sold')
    )
    
    # referral 
    # Step 1: Get policies with referrals via AgentPaymentDetails
    referral_qs = AgentPaymentDetails.objects.filter(
        policy__in=aggregation_qs,
        referral__isnull=False
    ).values('referral_id').annotate(
        policies_sold=Count('policy_id', distinct=True),
        policy_income=Sum(Cast('policy__policy_premium', FloatField())),
        total_net_premium=Sum(Cast('policy__policy_info__net_premium', FloatField())),
        total_gross_premium=Sum(Cast('policy__policy_info__gross_premium', FloatField())),
    ).order_by('-policy_income', '-policies_sold')

    # Step 2: Map referral IDs to names
    referral_map = {
        ref.id: ref.name for ref in Referral.objects.filter(id__in=[r['referral_id'] for r in referral_qs])
    }

    # Step 3: Convert to list and attach referral name
    referral_summary = list(referral_qs)
    referral_summary[:] = [
        {**item, 'referral_name': referral_map.get(item['referral_id'])}
        for item in referral_summary
        if referral_map.get(item['referral_id'])  # Skip if name not found
    ]

    # referral 
       # Step 1: Summary grouped by branch foreign key
    branch_summary = (
        aggregation_qs
        .exclude(policy_info__branch__isnull=True)
        .values('policy_info__branch')  # use foreign key ID
        .annotate(
            policies_sold=Count('id', distinct=True),
            policy_income=Sum(Cast('policy_premium', output_field=FloatField())),
            total_net_premium=Sum(Cast('policy_info__net_premium', output_field=FloatField())),
            total_gross_premium=Sum(Cast('policy_info__gross_premium', output_field=FloatField())),
        )
        .order_by('-policy_income', '-policies_sold')
    )

    # Step 2: Map branch ID to branch name
    branch_map = {
        branch.id: branch.branch_name
        for branch in Branch.objects.all()
    }

    # Step 3: Replace ID with actual branch name in results
    branch_summary = [
        {
            **item,
            'branch_name': branch_map.get(item['policy_info__branch'], f"Branch ID {item['policy_info__branch']}")
        }
        for item in branch_summary
        if item['policy_info__branch'] in branch_map
    ]



    # Step 1: Get policies with POS (agent_name = user ID)
    pos_qs = AgentPaymentDetails.objects.filter(
        policy__in=aggregation_qs,
        agent_name__isnull=False
    ).values('agent_name').annotate(
        policies_sold=Count('policy_id', distinct=True),
        policy_income=Sum(Cast('policy__policy_premium', FloatField())),
        total_net_premium=Sum(Cast('policy__policy_info__net_premium', FloatField())),
        total_gross_premium=Sum(Cast('policy__policy_info__gross_premium', FloatField())),
    ).order_by('-policy_income', '-policies_sold')

    # Step 2: Clean agent_name and collect valid user IDs
    valid_user_ids = [
        int(item['agent_name']) for item in pos_qs
        if item['agent_name'] and str(item['agent_name']).isdigit()
    ]

    # Step 3: Fetch users with valid names only
    users_qs = Users.objects.filter(id__in=valid_user_ids)
    users_map = {
        user.id: f"{user.first_name} {user.last_name}".strip()
        for user in users_qs
        if (user.first_name or user.last_name)
    }

    # Step 4: Prepare final POS summary — only if user name is present
    formatted_pos_summary = [
        {
            'pos_name': users_map[int(item['agent_name'])],
            'policies_sold': item['policies_sold'],
            'policy_income': item['policy_income'],
            'total_net_premium': item['total_net_premium'],
            'total_gross_premium': item['total_gross_premium'],
        }
        for item in pos_qs
        if item['agent_name']
        and str(item['agent_name']).isdigit()
        and int(item['agent_name']) in users_map  # skip if no valid name
    ]




    # Totals
    total_policies = aggregation_qs.count()
    status_counts = aggregation_qs.values('operator_verification_status').annotate(count=Count('id'))

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

            
    status_counts_quality = aggregation_qs.values('quality_check_status').annotate(count=Count('id'))

    pendingQuality = verifiedQuality = not_verifiedQuality = 0

    # Map status values to named variables
    for entry in status_counts_quality:
        status = entry['quality_check_status']
        count = entry['count']
        if status == '0':
            pendingQuality = count
        elif status == '1':
            verifiedQuality = count
        elif status == '2':
            not_verifiedQuality = count

    total_revenue = aggregation_qs.aggregate(
        total=Sum(Cast('policy_premium', output_field=FloatField()))
    )['total'] or 0

    total_net_premium = aggregation_qs.aggregate(
        total=Sum(Cast('policy_info__net_premium', FloatField()))
    )['total'] or 0

    total_gross_premium = aggregation_qs.aggregate(
        total=Sum(Cast('policy_info__gross_premium', FloatField()))
    )['total'] or 0

    # Monthly data with document count and total sum insured
    # Monthly data with document count and total sum insured
    with connection.cursor() as cursor:
        cursor.execute("""
           WITH RECURSIVE month_series AS (
                SELECT DATE_FORMAT(CURDATE() - INTERVAL 5 MONTH, '%Y-%m-01') AS month_start
                UNION ALL
                SELECT DATE_FORMAT(DATE_ADD(month_start, INTERVAL 1 MONTH), '%Y-%m-01')
                FROM month_series
                WHERE month_start < DATE_FORMAT(CURDATE(), '%Y-%m-01')
            )
            SELECT 
                DATE_FORMAT(ms.month_start, '%b') AS month_name,
                CONCAT(
                    COUNT(pd.id), 
                    ' - ₹', 
                    FORMAT(COALESCE(SUM(pd.sum_insured), 0), 0)
                ) AS document_summary
            FROM 
                month_series ms
            LEFT JOIN 
                policydocument pd 
                ON DATE_FORMAT(pd.created_at, '%Y-%m') = DATE_FORMAT(ms.month_start, '%Y-%m')
                AND pd.created_at >= CURDATE() - INTERVAL 6 MONTH
                AND pd.status = 6
            GROUP BY 
                ms.month_start
            ORDER BY 
                ms.month_start;

        """)
        result = cursor.fetchall()

    # Convert result rows to string, ensuring no `bytes` type in data
    monthly_data = [(row[0], row[1].decode('utf-8') if isinstance(row[1], bytes) else row[1]) for row in result]
    consolidated_month_labels = [row[0] for row in monthly_data]
    consolidated_month_counts = [row[1] for row in monthly_data]


    # Charts and summaries
    provider_labels = [entry['insurance_provider'] for entry in provider_summary]
    motor_counts = [entry['policies_sold'] for entry in provider_summary]
    insurer_motor_counts, insurer_provider_labels, insurer_sum_insured = business_summary_insurer_chart(request)
    policies_insurer_wise = insurer_wise_date(request)
    referral_agent_labels, referral_counts = referral_summary_chart(request)
    agent_labels, agent_counts = partner_policy_summary(request)
    summary = business_summary_product_wise(request)

    user_id = request.user.id
    role_id = request.user.role_id
    
    quotes = Quotation.objects.all()

    if role_id == 2:  # Management
        leads = Leads.objects.all()

    elif role_id == 3:  # Branch Manager
        managers = Users.objects.filter(role_id=5, senior_id=user_id)
        team_leaders = Users.objects.filter(role_id=6, senior_id__in=managers.values_list('id', flat=True))
        relationship_managers = Users.objects.filter(role_id=7, senior_id__in=team_leaders.values_list('id', flat=True))

        user_ids = list(managers.values_list('id', flat=True)) + \
                list(team_leaders.values_list('id', flat=True)) + \
                list(relationship_managers.values_list('id', flat=True)) + \
                [user_id]

        leads = Leads.objects.filter(Q(created_by_id__in=user_ids) | Q(assigned_to_id__in=user_ids))
    elif role_id == 4:  # Agent
        leads = Leads.objects.filter(Q(created_by_id=user_id) | Q(assigned_to_id=user_id))

    elif role_id == 5:  # Manager
        team_leaders = Users.objects.filter(role_id=6, senior_id=user_id)
        relationship_managers = Users.objects.filter(role_id=7, senior_id__in=team_leaders.values_list('id', flat=True))

        team_leader_ids = team_leaders.values_list('id', flat=True)
        rm_ids = relationship_managers.values_list('id', flat=True)
        user_ids = list(team_leader_ids) + list(rm_ids) + [user_id]

        leads = Leads.objects.filter(
            Q(created_by_id__in=user_ids) | Q(assigned_to_id__in=user_ids)
        )

    elif role_id == 6:  # Team Leader
        relationship_managers = Users.objects.filter(role_id=7, senior_id=user_id)
        rm_ids = relationship_managers.values_list('id', flat=True)
        user_ids = list(rm_ids) + [user_id]
        leads = Leads.objects.filter(
            Q(created_by_id__in=user_ids) | Q(assigned_to_id__in=user_ids)
        )

    elif role_id == 7:  # Relationship Manager
        leads = Leads.objects.filter(
            Q(created_by_id=user_id) | Q(assigned_to_id=user_id)
        )

    else:
        leads = Leads.objects.all()

    total_leads = leads.count()
    assigned_leads = leads.filter(assigned_to__isnull=False).count()
    fresh_leads = leads.filter(assigned_to__isnull=True).count()

    total_quotes = quotes.count()
    shared_quotes = quotes.filter(active=True).count()
    pending_quotes = quotes.filter(active=False).count()
    


    # PARTNER COUNTS 
    partners = Partner.objects.filter(partner_status='4').exclude(active=0)
    partner_ids = partners.values_list('user_id', flat=True)  # Get user IDs
    
    users = Users.objects.filter(id__in=partner_ids, activation_status=1)

    if role_id == 5:  # Manager
        team_leaders = Users.objects.filter(role_id=6, senior_id=user_id)
        relationship_managers = Users.objects.filter(role_id=7, senior_id__in=team_leaders.values_list('id', flat=True))

        user_ids = list(team_leaders.values_list('id', flat=True)) + \
                list(relationship_managers.values_list('id', flat=True)) 
        users = users.filter(senior_id__in=user_ids)
        total_partners = users.count()
    elif role_id == 6:  # Team Leader
        relationship_managers = Users.objects.filter(role_id=7, senior_id=user_id)
        user_ids = list(relationship_managers.values_list('id', flat=True))
        users = users.filter(senior_id__in=user_ids)
        total_partners = users.count()

    elif role_id == 7:  # Relationship Manager
        users = users.filter(senior_id=user_id)
        total_partners = users.count()
    else:
        total_partners = 0

    active_partners = 0
    inactive_partners = 0
    # PARTNER COUNTS 
    
    return render(request, 'dashboard.html', {
        'user': user,
        'provider_summary': provider_summary,
        'branch_summary': branch_summary,
        'formatted_pos_summary': formatted_pos_summary,
        'referral_summary': referral_summary,
        'total_quotation_count': total_quotation_count,
        
        'policies_insurer_wise': policies_insurer_wise,
        'consolidated_month_labels': consolidated_month_labels,
        'consolidated_month_counts': consolidated_month_counts,
        'insurer_motor_counts': insurer_motor_counts,
        'insurer_provider_labels': insurer_provider_labels,
        'insurer_sum_insured': insurer_sum_insured,
        'referral_counts': referral_counts,
        'agent_labels' : agent_labels,
        'agent_counts' : agent_counts,
        'referral_agent_labels': referral_agent_labels,
        'provider_labels': provider_labels,
        'summary': summary,
        'motor_counts': motor_counts,
        'policy_count': total_policies,
        'total_revenue': total_revenue,
        'total_net_premium': total_net_premium,
        'total_gross_premium': total_gross_premium,
        'pendingOperator': pendingOperator,
        'verifiedOperator': verifiedOperator,
        'not_verifiedOperator': not_verifiedOperator,
        'pendingQuality': pendingQuality,
        'verifiedQuality': verifiedQuality,
        'not_verifiedQuality': not_verifiedQuality,
        'total_leads': total_leads,
        'assigned_leads': assigned_leads,
        'fresh_leads': fresh_leads,
        'total_quotes': total_quotes,
        'shared_quotes': shared_quotes,
        'pending_quotes': pending_quotes,
        'total_partners': total_partners,
        'active_partners': active_partners,
        'inactive_partners': inactive_partners
    })

def insurer_wise_date(request):
    
    insurance_company =request.GET.get('insurance_company')

    policies = PolicyInfo.objects.filter(active='1').values(
        'policy_number','insurance_company','net_premium','gross_premium','created_at',
        'pos_name','policy_id')[:5]

    return policies

def business_summary_insurer_chart(request):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    filters = ""
    if start_date and end_date:
        filters = f"AND created_at BETWEEN '{start_date}' AND '{end_date}'"

    with connection.cursor() as cursor:
        cursor.execute(f"""
                SELECT 
                    pd.insurance_provider, 
                    COUNT(*) AS policies_sold, 
                    SUM(pi.gross_premium) AS total_sum_insured
                FROM 
                    policydocument pd
                LEFT JOIN 
                    policy_info pi 
                    ON pd.id = pi.policy_id AND pd.policy_number = pi.policy_number
                WHERE 
                    pd.status = 6
                    {filters}
                GROUP BY 
                    pd.insurance_provider
                ORDER BY 
                    policies_sold DESC
                LIMIT 8;
            """)

        result = cursor.fetchall()

    provider_summary = []
    insurer_motor_counts = []
    insurer_sum_insured = []  # New list for sum insured
    insurer_provider_labels = []

    for row in result:
        insurance_provider = row[0]
        policies_sold = row[1]
        total_sum_insured = row[2]  # Get the total sum insured
        initials = ''.join(word[0] for word in insurance_provider.split() if word).upper() if insurance_provider else ''

        provider_summary.append({
            'insurance_provider': insurance_provider,
            'policies_sold': policies_sold,
            'total_sum_insured': total_sum_insured,  # Include sum insured
            'initials': initials
        })

        insurer_motor_counts.append(policies_sold)
        insurer_sum_insured.append(total_sum_insured)  # Add sum insured to the list
        insurer_provider_labels.append(initials)

    return insurer_motor_counts, insurer_provider_labels, insurer_sum_insured  # Return sum insured


def business_summary_insurer_chartajax(request):
    filter_type = request.GET.get('filter')
    month = request.GET.get('month')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    where_clauses = []

    # Validate filter_type
    if not filter_type:
        return JsonResponse({'error': 'filter_type parameter is missing'}, status=400)

    if filter_type == "1":
        pass  # No filters applied
    elif filter_type == "2":  # Today
        where_clauses.append("DATE(pd.created_at) = CURDATE()")
    elif filter_type == "3" and month:  # MTD
        try:
            month = int(month)
            if not 1 <= month <= 12:
                return JsonResponse({'error': 'Invalid month parameter'}, status=400)
            where_clauses.append(f"MONTH(pd.created_at) = {month}")
            where_clauses.append("YEAR(pd.created_at) = YEAR(CURDATE())")
        except ValueError:
            return JsonResponse({'error': 'Invalid month parameter'}, status=400)
    elif filter_type == "4" and start_date and end_date:  # Custom range
        where_clauses.append(f"DATE(pd.created_at) BETWEEN '{start_date}' AND '{end_date}'")
    else:
        return JsonResponse({'error': 'Invalid filter_type or missing parameters'}, status=400)

    # Always add pd.status = 6 unless filter_type == 1
    if filter_type != "1":
        where_clauses.append("pd.status = 6")

    # Join WHERE conditions
    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    # Execute the query
    with connection.cursor() as cursor:
        cursor.execute(f"""
            SELECT 
                pd.insurance_provider, 
                COUNT(*) AS policies_sold, 
                SUM(pi.gross_premium) AS total_sum_insured
            FROM 
                policydocument pd
            LEFT JOIN 
                policy_info pi 
                ON pd.id = pi.policy_id AND pd.policy_number = pi.policy_number
            {where_sql}
            GROUP BY 
                pd.insurance_provider
            ORDER BY 
                policies_sold DESC
            LIMIT 8;
        """)
        result = cursor.fetchall()

    if not result:
        return JsonResponse({'message': 'No data found for the given filters'}, status=200)

    insurer_motor_counts = [row[1] for row in result]
    insurer_sum_insured = [row[2] for row in result]
    insurer_provider_labels = [
        ''.join(word[0] for word in row[0].split() if word).upper() if row[0] else ''
        for row in result
    ]

    return JsonResponse({
        'insurer_motor_counts': insurer_motor_counts,
        'insurer_provider_labels': insurer_provider_labels,
        'insurer_sum_insured': insurer_sum_insured
    })



def business_consolidated_ajax(request):
    filter_type = request.GET.get('filter')
    month = request.GET.get('month')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    # Default filter
    filters = "pd.status = 6"

    # Apply filter based on user selection
    if filter_type == "2":  # Today
        filters += " AND DATE(pd.created_at) = CURDATE()"
    elif filter_type == "3" and month:  # MTD
        filters += f" AND MONTH(pd.created_at) = {int(month)} AND YEAR(pd.created_at) = YEAR(CURDATE())"
    elif filter_type == "4" and start_date and end_date:  # Custom Range
        filters += f" AND DATE(pd.created_at) BETWEEN '{start_date}' AND '{end_date}'"
    else:  # Last 6 months by default
        filters += " AND pd.created_at >= CURDATE() - INTERVAL 6 MONTH"

    query = f"""
        WITH RECURSIVE month_series AS (
            SELECT DATE_FORMAT(CURDATE(), '%Y-%m-01') AS month_start
            UNION ALL
            SELECT DATE_FORMAT(DATE_ADD(month_start, INTERVAL -1 MONTH), '%Y-%m-01')
            FROM month_series
            WHERE month_start > DATE_FORMAT(CURDATE(), '%Y-%m-01') - INTERVAL 6 MONTH
        )
        SELECT 
            DATE_FORMAT(ms.month_start, '%b') AS month_name,
            COALESCE(COUNT(pd.id), 0) AS document_count,
            COALESCE(SUM(CAST(pi.gross_premium AS DECIMAL(10,2))), 0.00) AS total_sum_insured
        FROM 
            month_series ms
        LEFT JOIN 
            policydocument pd 
            ON DATE_FORMAT(pd.created_at, '%Y-%m') = DATE_FORMAT(ms.month_start, '%Y-%m')
        LEFT JOIN 
            policy_info pi 
            ON pd.id = pi.policy_id AND pd.policy_number = pi.policy_number
        WHERE 
            {filters} AND
            ms.month_start >= DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 5 MONTH), '%Y-%m-01')
        GROUP BY 
            ms.month_start
        ORDER BY 
            ms.month_start;
    """





    with connection.cursor() as cursor:
        cursor.execute(query)
        result = cursor.fetchall()

    monthly_data = [
        (row[0], row[1], float(row[2]) if row[2] is not None else 0.0)
        for row in result if row[0]
    ]
    
    consolidated_month_labels = [row[0] for row in monthly_data]
    consolidated_month_counts = [row[1] for row in monthly_data]
    consolidated_sum_insured = [row[2] for row in monthly_data]

    return JsonResponse({
        'monthly_data': monthly_data,
        'consolidated_month_labels': consolidated_month_labels,
        'consolidated_month_counts': consolidated_month_counts,
        'consolidated_sum_insured': consolidated_sum_insured
    })




def referral_summary_chart(request):
    with connection.cursor() as cursor:
        cursor.execute("""
        SELECT apd.agent_name, u.first_name, COUNT(apd.id) AS total_referrals
            FROM agent_payment_details apd
            INNER JOIN users u ON apd.agent_name = u.id
            WHERE apd.agent_name != 1
            GROUP BY apd.agent_name, u.first_name
            ORDER BY total_referrals DESC
            LIMIT 5;
        """)
        rows = cursor.fetchall()

    referral_counts = []
    referral_agent_labels = []

    
    for agent_name, first_name, total_referrals in rows:
        referral_counts.append(total_referrals)
        referral_agent_labels.append(first_name)

    return referral_agent_labels, referral_counts



def referral_summary_chartajax(request):
    filter_type = request.GET.get('filter')
    month = request.GET.get('month')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    filters = ""

    if filter_type == "2":  # Today
        filters = "DATE(apd.created_at) = CURDATE()"
    elif filter_type == "3" and month:  # MTD
        filters = f"MONTH(apd.created_at) = {int(month)} AND YEAR(apd.created_at) = YEAR(CURDATE())"
    elif filter_type == "4" and start_date and end_date:  # Custom
        filters = f"DATE(apd.created_at) BETWEEN '{start_date}' AND '{end_date}'"
            
     # Write your raw SQL query here
    query = f"""
       SELECT apd.agent_name, u.first_name, COUNT(apd.id) AS total_referrals
        FROM agent_payment_details apd
        INNER JOIN users u ON apd.agent_name = u.id
        WHERE apd.agent_name != 1
       {"AND " + filters if filters else ""}
        GROUP BY apd.agent_name, u.first_name
        ORDER BY total_referrals DESC
        LIMIT 5;
    """
    
    # Execute the query
    with connection.cursor() as cursor:
        cursor.execute(query)
        result = cursor.fetchall()

        print(result)

    # Process the result
    referral_counts = [row[2] for row in result]  # total_referrals is in the 3rd column (index 2)
    referral_agent_labels = [
        row[1] if row[1] else f"Agent {row[0]}"  # first_name is in the 2nd column (index 1)
        for row in result
    ]

    print("Referral Counts:", referral_counts)
    print("Referral Agent Labels:", referral_agent_labels)


    return JsonResponse({
        'referral_counts': referral_counts,
        'referral_agent_labels': referral_agent_labels
    })


def partner_policy_summary(request):
    user = request.user

    # Step 1: Filter policies
    
    base_qs = PolicyDocument.objects.filter(status=6)

    aggregation_qs = base_qs.filter(policy_info__isnull=False).distinct()

    # Step 2: Get agent policy counts
    pos_qs = AgentPaymentDetails.objects.filter(
        policy__in=aggregation_qs,
        agent_name__isnull=False
    ).values('agent_name').annotate(
        policies_sold=Count('policy_id', distinct=True)
    ).order_by('-policies_sold')

    
    if not pos_qs:
        return [], []
    # Step 3: Prepare agent IDs safely
    agent_ids = [
        int(item['agent_name']) for item in pos_qs
        if str(item['agent_name']).strip().isdigit()
    ]
    users_map = {
        user.id: f"{user.first_name} {user.last_name}".strip() or user.user_name
        for user in Users.objects.filter(id__in=agent_ids)
    }

    # Step 4: Prepare labels and counts
    agent_labels = []
    agent_counts = []

    for item in pos_qs:
        raw_id = str(item['agent_name']).strip()
        if raw_id.isdigit():
            agent_id = int(raw_id)
            agent_name = users_map.get(agent_id, f"Agent {agent_id}")
            agent_labels.append(agent_name)
            agent_counts.append(item['policies_sold'])
       

    # Optional: Debug output
    print("Agent Labels:", agent_labels)
    print("Agent Counts:", agent_counts)

    return  agent_labels, agent_counts
    

def partner_policy_summary_ajax(request):
    user = request.user

    base_qs = PolicyDocument.objects.filter(status=6)

    aggregation_qs = base_qs.filter(policy_info__isnull=False).distinct()

    pos_qs = AgentPaymentDetails.objects.filter(
        policy__in=aggregation_qs,
        agent_name__isnull=False
    ).values('agent_name').annotate(
        policies_sold=Count('policy_id', distinct=True)
    ).order_by('-policies_sold')

    if not pos_qs:
        return JsonResponse({'agent_data': []}, status=200)

    agent_ids = [
        int(item['agent_name']) for item in pos_qs 
        if str(item['agent_name']).strip().isdigit()
    ]
    users_map = {
        user.id: f"{user.first_name} {user.last_name}".strip() or user.user_name
        for user in Users.objects.filter(id__in=agent_ids)
    }

    agent_labels = []
    agent_counts = []
  
    for item in pos_qs:
        raw_id = str(item['agent_name']).strip()
        if raw_id.isdigit():
            agent_id = int(raw_id)
            agent_name = users_map.get(agent_id, f"Agent {agent_id}")
            agent_labels.append(agent_name)
            agent_counts.append(item['policies_sold'])

    return JsonResponse({
        'agent_labels' : agent_labels,
        'agent_counts' : agent_counts
    })


def dashboard_ajax(request):
    
    base_qs = PolicyDocument.objects.filter(status=6)

    # Collect selected filter values
    consolidated_by = request.GET.get('consolidated_by', '1')
    month = request.GET.get('consolidated_by_month', '')
    consolidated_from_date = request.GET.get('consolidated_from_date', '')
    consolidated_to_date = request.GET.get('consolidated_to_date', '')

    filters = "WHERE pd.status = 6"

    if consolidated_by == "2":  # Today
        filters += " AND DATE(pd.created_at) = CURDATE()"

    elif consolidated_by == "3" and month:  # MTD
        try:
            filters += f" AND MONTH(pd.created_at) = {int(month)} AND YEAR(pd.created_at) = YEAR(CURDATE())"
        except (IndexError, ValueError):
            return JsonResponse({'error': 'Invalid month format.'}, status=400)

    elif consolidated_by == "4" and  consolidated_from_date and consolidated_to_date:  # Custom Range
        filters += f" AND DATE(pd.created_at) BETWEEN '{consolidated_from_date}' AND '{consolidated_to_date}'"


    # Prepare the raw SQL query with safe parameters
    sql_query = f"""
        SELECT 
            COUNT(DISTINCT pd.id) AS policies_sold, 
            SUM(COALESCE(CAST(pi.net_premium AS DECIMAL(10,2)), 0)) AS total_net_premium, 
            SUM(COALESCE(CAST(pi.gross_premium AS DECIMAL(10,2)), 0)) AS total_gross_premium 
        FROM 
            policydocument pd 
        JOIN 
            policy_info pi ON pi.policy_id = pd.id 
            {filters};
    """

    # Execute the raw SQL query with parameters
    with connection.cursor() as cursor:
        cursor.execute(sql_query)
        result = cursor.fetchall()

    # Check if result is not None
    if result:
        policies_sold = result[0][0] or 0
        total_net_premium = float(result[0][1]) if result[0][1] is not None else 0.0
        total_gross_premium = float(result[0][2]) if result[0][2] is not None else 0.0
        data = {
            'policies_sold':policies_sold ,  # Get the first value from the result
            'total_net_premium': total_net_premium ,  # Get the second value from the result
            'total_gross_premium': total_gross_premium,  # Get the third value from the result
        }
        return JsonResponse(data)
    else:
        return JsonResponse({
            'policies_sold': 0,
            'total_net_premium': 0.0,
            'total_gross_premium': 0.0
        })

def business_summary_product_wise(request):

    summary = PolicyDocument.objects.exclude(vehicle_type__isnull=True)\
                                    .exclude(vehicle_type__exact='')\
                                    .values('vehicle_type') \
                                    .annotate(product_count=Count('vehicle_type')) \
                                    .order_by('vehicle_type').distinct()
    return summary  


def business_summary_product_wiseajax(request):
    summary = PolicyDocument.objects.exclude(vehicle_type__isnull=True) \
                                    .exclude(vehicle_type__exact='') \
                                    .values('vehicle_type') \
                                    .annotate(product_count=Count('vehicle_type')) \
                                    .distinct()

    total_count = sum(item['product_count'] for item in summary)

    return JsonResponse({
        'product_wise_labels': ["2W/4 Wheeler"],
        'product_wise_counts': [total_count],
        'productCommercialLabels': ["Commercial"],
        'productCommercialCounts': [total_count], 
    }, safe=False)