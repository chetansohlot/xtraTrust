from ..models import UploadedZip, FileAnalysis, ExtractedFile, BulkPolicyLog, Commission, PolicyDocument, UnprocessedPolicyFiles, ChatGPTLog, UploadedExcel
from ..models import PolicyInfo, PolicyVehicleInfo, AgentPaymentDetails, InsurerPaymentDetails, FranchisePayment
from ..models import FranchisePaymentLog, PolicyInfoLog, PolicyVehicleInfoLog, AgentPaymentDetailsLog, InsurerPaymentDetailsLog
import django, dramatiq, fitz, os, zipfile, requests, re, json, traceback, time, logging, shutil
from django.conf import settings
from django.utils import timezone
from django.utils.timezone import now
from django_q.tasks import async_task
OPENAI_API_KEY = settings.OPENAI_API_KEY
from django.db.models import F
from ..utils import getUserNameByUserId, commisionRateByMemberId, insurercommisionRateByMemberId, to_int
from django.core.exceptions import ObjectDoesNotExist
from django.utils.encoding import filepath_to_uri
import pandas as pd
import openpyxl, re, datetime, logging
from django.utils import timezone
from dateutil import parser
from django.contrib.auth.hashers import make_password
from ..models import Leads, LeadUploadExcel, Users
from dateutil import parser
from django.db.models import Q
logger = logging.getLogger(__name__)

def process_lead_excel(lead_upload_excel_id):
    try:
        # Get the LeadUploadExcel instance
        upload_instance = LeadUploadExcel.objects.get(id=lead_upload_excel_id)
        excel_file = upload_instance.file

        # Load the Excel file
        wb = openpyxl.load_workbook(excel_file)
        sheet = wb.active

        inserted = 0
        duplicate_data_found = False


        
        start_num = 1  

        for index, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
            if len(row) < 29 or any(cell is None for cell in row[:13]):
                logger.warning(f"Row {index} skipped: Incomplete data.")
                continue

            try:
                mobile_number = str(row[0]).strip()
                email_address = str(row[1]).strip()
                quote_date = row[2]
                name_as_per_pan = str(row[3]).strip()
                pan_card_number = str(row[4]).strip().upper()
                date_of_birth = row[5]
                state = str(row[6]).strip()
                city = str(row[7]).strip()
                pincode = str(row[8]).strip()
                lead_source = str(row[9]).strip()
                address = str(row[10]).strip()
                lead_description = str(row[11]).strip()
                lead_type = str(row[12]).strip()

                # New fields
                policy_date = row[13]
                sales_manager = str(row[14]).strip()
                agent_name = str(row[15]).strip()
                insurance_company = str(row[16]).strip()
                policy_type = str(row[17]).strip()
                policy_number = str(row[18]).strip()
                vehicle_type = str(row[19]).strip()
                make_and_model = str(row[20]).strip()
                fuel_type = str(row[21]).strip()
                registration_number = str(row[22]).strip()
                manufacturing_year = row[23]
                sum_insured = row[24]
                ncb = row[25]
                od_premium = row[26]
                tp_premium = row[27]
                risk_start_date = row[28]

                # VALIDATIONS (same logic as before)
                if not re.fullmatch(r'[6-9]\d{9}', mobile_number):
                    logger.warning(f"Row {index} skipped: Invalid mobile number - {mobile_number}")
                    continue

                if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email_address):
                    logger.warning(f"Row {index} skipped: Invalid email - {email_address}")
                    continue

                if not re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]$', pan_card_number):
                    logger.warning(f"Row {index} skipped: Invalid PAN - {pan_card_number}")
                    continue
                try:
                    dob = parser.parse(str(date_of_birth)).date()
                except Exception:
                    logger.warning(f"Row {index} skipped: Invalid DOB - {date_of_birth}")
                continue

                try:
                    policy_date = datetime.strptime(str(policy_date), "%Y-%m-%d").date() if policy_date else None
                except:
                    policy_date = None

                try:
                    risk_start_date = datetime.strptime(str(risk_start_date), "%Y-%m-%d").date() if risk_start_date else None
                except:
                    risk_start_date = None

                # Duplicate check
                if Leads.objects.filter(
                    Q(mobile_number=mobile_number) |
                    Q(email_address=email_address) |
                    Q(pan_card_number=pan_card_number)
                ).exists():
                    logger.info(f"Row {index} skipped: Duplicate entry.")
                    duplicate_data_found = True
                    continue

                # Create lead_id
                lead_id = f"L{start_num:05d}"
                start_num += 1

                # Insert into DB
                Leads.objects.create(
                    lead_id=lead_id,
                    mobile_number=mobile_number,
                    email_address=email_address,
                    quote_date=quote_date,
                    name_as_per_pan=name_as_per_pan,
                    pan_card_number=pan_card_number,
                    date_of_birth=dob,
                    state=state,
                    city=city,
                    pincode=pincode,
                    lead_source=lead_source,
                    address=address,
                    lead_description=lead_description,
                    lead_type=lead_type,
                    policy_date=policy_date,
                    sales_manager=sales_manager,
                    agent_name=agent_name,
                    insurance_company=insurance_company,
                    policy_type=policy_type,
                    policy_number=policy_number,
                    vehicle_type=vehicle_type,
                    make_and_model=make_and_model,
                    fuel_type=fuel_type,
                    registration_number=registration_number,
                    manufacturing_year=manufacturing_year,
                    sum_insured=sum_insured,
                    ncb=ncb,
                    od_premium=od_premium,
                    tp_premium=tp_premium,
                    net_premium=(od_premium or 0) + (tp_premium or 0),
                    gross_premium=(od_premium or 0) + (tp_premium or 0),
                    risk_start_date=risk_start_date
                )
                inserted += 1

            except Exception as e:
                logger.error(f"Row {index} error: {e}")
                continue

        # Final messages
        if inserted > 0:
            logger.info(f"{inserted} leads uploaded successfully.")
        elif duplicate_data_found:
            logger.warning("No new leads were inserted. All records were duplicates.")
        else:
            logger.info("No valid data found in Excel file!")

    except Exception as e:
        logger.error(f"Error processing Excel file: {e}")