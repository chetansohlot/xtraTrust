# from empPortal.controller.Referral import generate_referral_code
from empPortal.controller.Referral import generate_referral_code
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
from empPortal.model import Referral
import os
from empPortal.models import RefUploadedExcel 
# from empPortal.utils import generate_referral_code  # Update with your actual import
from django.db.models import Q
import logging

logger = logging.getLogger(__name__)

# def refBulkUpload(file_id):
#     try:
#         excel_instance = RefUploadedExcel.objects.get(id=file_id)
#         file_path = excel_instance.file.path
        
#         try:
#            # Save file_name and file_url
#            excel_instance.file_name = os.path.basename(file_path)
#            excel_instance.file_url = settings.MEDIA_URL + excel_instance.file.name  # If you're serving media via MEDIA_URL
#            excel_instance.save()
#         except Exception as e:
#                logger.error(f"[Referral Upload] File ID {file_id}: Failed to update file_name/file_url - {str(e)}")

#         df = pd.read_excel(file_path)
        
#         total_rows = len(df)
#         valid_rows = 0
#         invalid_rows = 0
#         success_rows = 0

#         for index, row in df.iterrows():
#                 name = str(row.get('Name', '')).strip()
#                 user_role = str(row.get('User Role', '')).strip()
#                 branch = str(row.get('Branch', '')).strip()
#                 sales = str(row.get('Sales Manger', '')).strip()
#                 supervisor = str(row.get('Supervisor', '')).strip()
#                 franchise = str(row.get('Franchise', '')).strip()
#                 mobile = str(row.get('Mobile Number', '')).strip()
#                 email = str(row.get('Email', '')).strip()
#                 dob = row.get('Date of Birth')
#                 date_of_anniversary = row.get('Anniversary Date')
#                 address = str(row.get('Address', '')).strip()
#                 pincode = str(row.get('Pincode', '')).strip()
#                 city = str(row.get('City', '')).strip()
#                 state = str(row.get('State', '')).strip()
#                 pan_card_number = str(row.get('Pan Number', '')).upper().strip() 
#                 aadhar_no = str(row.get('Aadhar Number', '')).strip()


#                 ## Validation In Excel Sheets ## 
#                 if not name or not mobile or not email or not pan_card_number or not aadhar_no:
#                     continue
#                 if Referral.objects.filter(
#                      Q(mobile=mobile) | Q(email=email) | Q(pan_card_number=pan_card_number) | Q(aadhar_no=aadhar_no)
#                     ).exists():
#                      logger.error(f"Row{index + 2} skipped: Duplicate mobile number, email, Pan card, Aadhar number")
#                      continue
                
#                 ## Validation On field Excel Sheets ##
#                 if not re.match(r"^[6-9][0-9]{9}$",str(mobile)):
#                      logger.error(f"Row{index + 2} skipped: Invalid mobile number format")
#                      continue
                
#                 if not re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]$',str(pan_card_number)):
#                     logger.error(f"Row{index + 2} skipped: Invalid Pan number format")
#                     continue

#                 if not re.match(r'^[2-9][0-9]{11}$', str(aadhar_no)):
#                     logger.error(f"Row{index + 2} skipped:Invalid Aadhar number format. I will have 12 digit, Not start with 0 and 1")
#                     continue

#                 # if Referral.objects.filter(email=email).exists():
#                 #     continue
#                 # if Referral.objects.filter(pan_card_number=pan_card_number).exists():
#                 #     continue
#                 # if Referral.objects.filter(aadhar_no=aadhar_no).exists():
#                 #     continue


#                 Referral.objects.create(
#                     name=name,
#                     user_role=user_role,
#                     branch=branch,
#                     sales=sales,
#                     supervisor=supervisor,
#                     franchise=franchise,
#                     mobile=mobile,
#                     email=email,
#                     dob=dob if pd.notnull(dob) else None,
#                     date_of_anniversary=date_of_anniversary if pd.notnull(date_of_anniversary) else None,
#                     address=address,
#                     pincode=pincode,
#                     city=city,
#                     state=state,
#                     pan_card_number=pan_card_number,
#                     aadhar_no=aadhar_no,
#                     referral_code=generate_referral_code(),
#                     created_at=now(),
#                     updated_at=now(),
#                 )



#         excel_instance.total_rows = total_rows
#         excel_instance.valid_rows = valid_rows
#         excel_instance.invalid_rows = invalid_rows
#         excel_instance.success_rows = success_rows
#         excel_instance.is_processed = True
#         excel_instance.save()

#     except Exception as e:
#         logger.error(f"[Referral Upload] File ID {file_id}: Unexpected error - {str(e)}")
#         try:
#             excel_instance.error = str(e)
#             excel_instance.is_processed = True
#             excel_instance.save()
#         except:
#             pass



def refBulkUpload(file_id):
    try:
        # Get the RefUploadedExcel instance
        excel_instance = RefUploadedExcel.objects.get(id=file_id)
        file_path = excel_instance.file.path
        
        # Try to save file_name and file_url
        try:
            excel_instance.file_name = os.path.basename(file_path)
            excel_instance.file_url = settings.MEDIA_URL + excel_instance.file.name  # If you're serving media via MEDIA_URL
            excel_instance.save()
        except Exception as e:
            logger.error(f"[Referral Upload] File ID {file_id}: Failed to update file_name/file_url - {str(e)}")

        # Read the Excel file into a DataFrame
        df = pd.read_excel(file_path)

        total_rows = len(df)
        valid_rows = 0
        invalid_rows = 0
        success_rows = 0
        error_logs = []

        # Iterate over each row in the DataFrame
        for index, row in df.iterrows():
            row_num = index + 2  # +2 to account for 0-indexing and header

            try:
                name = str(row.get('Name', '')).strip()
                user_role = str(row.get('User Role', '')).strip()
                branch = str(row.get('Branch', '')).strip()
                sales = str(row.get('Sales Manger', '')).strip()
                supervisor = str(row.get('Supervisor', '')).strip()
                franchise = str(row.get('Franchise', '')).strip()
                mobile = str(row.get('Mobile Number', '')).strip()
                email = str(row.get('Email', '')).strip()
                dob = row.get('Date of Birth')
                date_of_anniversary = row.get('Anniversary Date')
                address = str(row.get('Address', '')).strip()
                pincode = str(row.get('Pincode', '')).strip()
                city = str(row.get('City', '')).strip()
                state = str(row.get('State', '')).strip()
                pan_card_number = str(row.get('Pan Number', '')).upper().strip() 
                aadhar_no = str(row.get('Aadhar Number', '')).strip()

                # Required field validation
                if not name or not mobile or not email or not pan_card_number or not aadhar_no:
                    invalid_rows += 1
                    error_logs.append(f"Row {row_num}: Missing required fields")
                    continue

                # Duplicate check
                if Referral.objects.filter(
                    Q(mobile=mobile) | Q(email=email) | Q(pan_card_number=pan_card_number) | Q(aadhar_no=aadhar_no)
                ).exists():
                    invalid_rows += 1
                    error_logs.append(f"Row {row_num}: Duplicate entry found")
                    continue

                # Mobile format validation
                if not re.match(r"^[6-9][0-9]{9}$", mobile):
                    error_msg = f"Row {row_num}: Invalid mobile number"
                    invalid_rows += 1
                    error_logs.append(error_msg)
                    logger.warning(f"[Referral Upload] {error_msg}")
                    continue

                # PAN format validation
                if not re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]$', pan_card_number):
                    invalid_rows += 1
                    error_logs.append(f"Row {row_num}: Invalid PAN number")
                    continue

                # Aadhar format validation
                if not re.match(r'^[2-9][0-9]{11}$', aadhar_no):
                    invalid_rows += 1
                    error_logs.append(f"Row {row_num}: Invalid Aadhar number")
                    continue

                # Passed all validations
                valid_rows += 1

                # Create the referral
                referral = Referral.objects.create(
                    name=name,
                    user_role=user_role,
                    branch=branch,
                    sales=sales,
                    supervisor=supervisor,
                    franchise=franchise,
                    mobile=mobile,
                    email=email,
                    dob=dob if pd.notnull(dob) else None,
                    date_of_anniversary=date_of_anniversary if pd.notnull(date_of_anniversary) else None,
                    address=address,
                    pincode=pincode,
                    city=city,
                    state=state,
                    pan_card_number=pan_card_number,
                    aadhar_no=aadhar_no,
                    referral_code=generate_referral_code(),
                    created_at=now(),
                    updated_at=now(),
                )
                success_rows += 1
                logger.info(f"Row {row_num} successfully added to the database.")

            except Exception as row_error:
                invalid_rows += 1
                error_logs.append(f"Row {row_num}: Unexpected error - {str(row_error)}")

        # Update the Excel instance with totals and errors
        excel_instance.total_rows = total_rows
        excel_instance.valid_rows = valid_rows
        excel_instance.invalid_rows = invalid_rows
        excel_instance.success_rows = success_rows
        excel_instance.is_processed = True
        excel_instance.save()

        logger.info(f"Bulk upload for file {file_id} completed successfully.")
        logger.info(f"Background task finished - Sucess: {success_rows}, Errors: {invalid_rows} .")

        
        return excel_instance

    except Exception as e:
        logger.error(f"[Referral Upload] File ID {file_id}: Unexpected error - {str(e)}")
        try:
            excel_instance.error = str(e)
            excel_instance.is_processed = True
            excel_instance.save()
        except:
            pass
        return None



