from django_cron import CronJobBase, Schedule
from empPortal.models import PolicyDocument, FileAnalysis, ExtractedFile
from empPortal.models import BulkPolicyLog, PolicyInfo, AgentPaymentDetails, FranchisePayment, InsurerPaymentDetails, PolicyVehicleInfo,SingleUploadFile
from django_q.tasks import async_task
from django.utils import timezone
from django.utils.encoding import filepath_to_uri
from empPortal.utils import chatPdfMessage, commisionRateByMemberId, insurercommisionRateByMemberId, getUserNameByUserId
from datetime import datetime
from django.conf import settings
import logging, os, shutil, zipfile, requests, re, json, ast

logger = logging.getLogger(__name__)

class ReprocessPoliciesCronJob(CronJobBase):
    RUN_EVERY_MINS = 1  # every 3 minutes

    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)
    code = 'empPortal.reprocess_policies_cron'  # Unique code for the cron job

    def do(self):
        # Fetch all policies with status == 4
        policies_to_reprocess = PolicyDocument.objects.exclude(status__in=[6, 7])

        for policy in policies_to_reprocess:
            try:
                # You can use a more complex logic to get the file_obj or task as needed
                file_obj = ExtractedFile.objects.filter(policy_id=policy.id).last()
                print(file_obj.id)
                logger.info(f"Something Missing {file_obj.id}")

                async_task('empPortal.tasks.reprocessFiles', file_obj.id)

            except PolicyDocument.DoesNotExist:
                print(f"File with ID {policy.id} not found in PolicyDocument")
            
            except FileAnalysis.DoesNotExist:
                print(f"File with ID {policy.id} not found in FileAnalysis")
                
            except ExtractedFile.DoesNotExist:
                print(f"File with ID {policy.id} not found in ExtractedFile")
        
        print(f"Reprocessed policies with status 4 at {timezone.now()}")

class ExtractFilesFromZip(CronJobBase):
    RUN_EVERY_MINS = 1
    
    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)
    code = 'empPortal.extract_files_from_zip'
    
    def do(self):
        try:
            # Fetch First 10 zips with is_processed = 0
            uploaded_zips_ids = []
                        
            cutoff_time = datetime.strptime('2025-04-24 01:01', '%Y-%m-%d %H:%M')
            zips = BulkPolicyLog.objects.filter(is_processed=0, created_at__gte=cutoff_time)[:10]
            for zip_entry in zips:
                try:
                    pdf_file_ids = []
                    zip_path = zip_entry.file.path
                    extract_dir = os.path.join(settings.MEDIA_ROOT,'extracted',str(zip_entry.id))
                    
                    # if path exist remove the path
                    if os.path.exists(extract_dir):
                        shutil.rmtree(extract_dir)
                        
                    # create new path for zip extraction
                    os.makedirs(extract_dir,exist_ok=True)
                    
                    # with zipfile.ZipFile(zip_path,'r') as zip_ref:
                    #     zip_ref.extractall(extract_dir)
                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        for member in zip_ref.infolist():
                            if member.is_dir():
                                continue
                            if "/" in member.filename or "\\" in member.filename:
                                continue
                            
                            extracted_path = os.path.join(extract_dir, member.filename)
                            with open(extracted_path, "wb") as f:
                                f.write(zip_ref.read(member.filename))
                        
                    for filename in os.listdir(extract_dir):
                        if not filename.lower().endswith('.pdf'):
                            zip_entry.count_not_pdf += 1
                            zip_entry.save() 
                            logger.warning(f"file is not pdf ,path: {filename}")
                            continue  # skip non-pdf files
                        
                        
                        file_path = os.path.join(extract_dir,filename)
                        relative_path = os.path.relpath(file_path,settings.MEDIA_ROOT)
                        file_url = filepath_to_uri(os.path.join(settings.MEDIA_URL,relative_path))
                        
                        try:
                            existing_file = ExtractedFile.objects.filter(
                                bulk_log_ref=zip_entry,
                                file_path=relative_path
                            ).first()
                            if existing_file:
                                # zip_entry.count_uploaded_files += 1
                                # zip_entry.count_duplicate_files += 1
                                # if(zip_entry.count_uploaded_files >= zip_entry.count_pdf_files):
                                #     zip_entry.is_processed=True
                                #     zip_entry.status=3
                                # zip_entry.save()
                                # existing_file.status = 7
                                # existing_file.save()
                                continue
                            else:
                                extracted = ExtractedFile.objects.create(
                                    bulk_log_ref=zip_entry,
                                    file_path=relative_path,
                                    filename=filename,
                                    file_url=file_url,
                                )
                                
                            zip_entry.count_pdf_files += 1
                            pdf_file_ids.append(extracted.id)
                            logger.info(f"File is saved in extracted_file for bulk_log_id: {zip_entry.id} and file_name : {filename}")
                        except Exception as e:
                            logger.error(f"Error in processing file_path {file_path} and file_name {filename}: {str(e)}")
                            continue
                    
                except Exception as e:
                    logger.error(f"Unknown Error in ExtractFilesFromZip Cron Error: {str(e)}")
                    continue
                
                zip_entry.status = 2
                zip_entry.save()
                uploaded_zips_ids.append(zip_entry.id)
                logger.info(f"Zip is completely extracted for bulk_log_id: {zip_entry.id}")
            logger.info(f"Completely extracted for bulk_log_ids: {uploaded_zips_ids}")
        except Exception as e:
            logger.error(f"Unknown Error in ExtractFilesFromZip Cron Job: {str(e)}")
            
class GettingSourceIdForSinglePolicies(CronJobBase):
    RUN_EVERY_MINS = 1
    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)
    code = 'empPortal.getting_source_id_for_single_policies'
    def do(self):
        try:
            cutoff_time = datetime.strptime('2025-04-24 01:01', '%Y-%m-%d %H:%M')
            
            files = SingleUploadFile.objects.filter(
                source_id__isnull=True,
                is_uploaded=False,
                extracted_at__gte=cutoff_time,
                is_failed__isnull=False,
                retry_source_count__lte=2
            )[:10]
            
            if len(files) > 0:
                for file in files:
                    pdf_path = file.file_path.path
                    file.status = 1
                    file.save()
                    if os.path.exists(pdf_path):
                        try:
                            headers = {
                                'x-api-key': settings.CHATPDF_API_KEY
                            }
                            with open(pdf_path, 'rb') as f:
                                open_files = [('file', (file.filename, f, 'application/pdf'))]
                                response = requests.post(settings.CHATPDF_SOURCE_API_URL, headers=headers, files=open_files)
                                
                            if response.status_code == 200:
                                source_id = response.json().get('sourceId')
                                file.source_id = source_id
                                file.status = 2
                                file.retry_source_count += 1
                                file.is_uploaded = True
                                file.save()
                                
                                logger.info(f"Updated source_id for single_file_id: {file.id}, filename: {file.filename}, Source ID: {source_id}")
                            else:
                                file.retry_source_count += 1
                                if file.retry_source_count >=2:
                                    file.is_failed = True
                                file.save()
                                logger.error(f"Failed to upload single_policy_file_id {file.id}. Status: {response.status_code}, Error: {response.text}")
                                continue
                        except Exception as e:
                            logger.error(f"Error for single_policy_file_id: {file.id}, Error: {str(e)}")
                    else:
                        logger.error(f"PDF file not found for single_policy_file_id: {file.id}")
                logger.info(f"Complete GettingSourceIdForSinglePolicies Cron Job")
            else:
                logger.info(f"Do not require processing in GettingSourceIdForSinglePolicies.")
        except Exception as e:
            logger.error(f"Unknown Error in GettingSourceIdForSinglePolicies Cron Job: {str(e)}")
              
class GettingPdfExtractedDataSinglePolicies(CronJobBase):
    RUN_EVERY_MINS = 1
    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)
    code = 'empPortal.getting_pdf_extracted_data_single_policies'
    
    def do(self):
        try:
            
            cutoff_time = datetime.strptime('2025-04-24 01:01', '%Y-%m-%d %H:%M')

            files = SingleUploadFile.objects.filter(
                source_id__isnull=False,
                is_uploaded=True,
                extracted_at__gte=cutoff_time,
                policy_id__isnull=True,
                retry_chat_response_count__lte=2,
                is_failed__isnull=False
            )[:10]
            if len(files) > 0:
                for file in files:
                    if not file.source_id:
                        logger.error(f"No source_id found for single_policy_file_id {file.id}")
                        continue
                    try:
                        file.status = 3
                        file.retry_chat_response_count += 1
                        if file.retry_chat_response_count >=2:
                            file.is_failed = True
                        file.save()
                        headers = {
                            'x-api-key': settings.CHATPDF_API_KEY,
                            "Content-Type": "application/json",
                        }
                        
                        message = chatPdfMessage()
                        data = {
                            'sourceId': file.source_id,
                            'messages': [
                                {
                                    'role': "user",
                                    'content': message
                                }
                            ]
                        }
                        
                        response = requests.post(
                            settings.CHATPDF_CHAT_API_URL,
                            headers=headers,
                            json=data
                        )
                        
                        logger.info(f"Status Code for Single Policy Extracting Data for single_policy_file_id:{file.id} is {response.status_code}")
                        
                        if response.status_code == 200:
                            result = response.json().get('content')
                            logger.info(f"Extracting Data for single_policy_file_id:{file.id} is {result}")
                            
                            if isinstance(result, str):
                                cleaned_result = re.sub(r'```(?:json)?\s*|\s*```', '', result).strip()
                                extracted_data = json.loads(cleaned_result)
                            else:
                                extracted_data = result
                                
                            
                            file.chat_response = extracted_data
                            file.is_extracted = True
                            file.status = 4
                            file.save()
                        else:
                            logger.error(f"ChatPDF API failed for single_policy_file_id {file.id}. Status: {response.status_code}, Error: {response.text}")
                            continue
                    except Exception as e:
                        logger.error(f"Error in api of pdf text extraction for single_policy_file_id: {file.id} is {str(e)}")
                
                logger.info(f"Complete execute GettingPdfExtractedDataSinglePolicies.")
            else:
                logger.info(f"Do not require processing in GettingPdfExtractedDataSinglePolicies .")
                    
        except Exception as e:
            logger.error(f"Unknown Error in GettingPdfExtractedDataSinglePolicy, Error{str(e)}")
            
class CreateNewPolicySinglePolicy(CronJobBase):
    RUN_EVERY_MINS = 1
    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)
    code = 'empPortal.create_new_policy_single_policy'
    
    def do(self):
        try:
            file_ids = []
            cutoff_time = datetime.strptime('2025-04-24 01:01', '%Y-%m-%d %H:%M')
            files = SingleUploadFile.objects.filter(is_failed__isnull=False,policy_id__isnull = True, extracted_at__gte=cutoff_time,retry_creating_policy_count__lte=2,is_extracted=True)[:10]
            if len(files)>0:
                for file in files:
                    file.status = 5
                    file.retry_creating_policy_count += 1
                    if file.retry_creating_policy_count >=2:
                        file.is_failed = True
                    file.save()
                    file_ids.append(file.id)
                    extracted_data = file.chat_response
                    if extracted_data:
                        if isinstance(extracted_data, str):
                            try:
                                extracted_data = ast.literal_eval(extracted_data)
                                if extracted_data.get('policy_number') and extracted_data.get('insurance_company'):
                                    policy_number = extracted_data.get('policy_number', '')
                                    vehicle_number = extracted_data.get('vehicle_number', '')
                                    
                                    try:
                                        policy_exist = PolicyDocument.objects.filter(policy_number=policy_number).exists()
                                        if policy_exist:
                                            try:
                                                file.status = 7
                                                file.policy_id = policy_exist
                                                file.is_completed = True
                                                file.save()
                                            except Exception as e:
                                                logger.error(f"Error in updating policy in CreateNewPolicySinglePolicy job for single_file_id: {file.id}")
                                                continue
                                        else:
                                            try:
                                                rm_id = file.create_by_id
                                                insurance_company_id = file.insurance_company_id
                                                rm_name = getUserNameByUserId(rm_id)
                                                commision_rate = commisionRateByMemberId(rm_id)
                                                insurer_rate = insurercommisionRateByMemberId(1)
                                                if commision_rate:
                                                    od_percentage = commision_rate.od_percentage
                                                    net_percentage = commision_rate.net_percentage
                                                    tp_percentage = commision_rate.tp_percentage
                                                else:
                                                    od_percentage = 0.0
                                                    net_percentage = 0.0
                                                    tp_percentage = 0.0
                                                    
                                                if insurer_rate:
                                                    insurer_od_percentage = insurer_rate.od_percentage
                                                    insurer_net_percentage = insurer_rate.net_percentage
                                                    insurer_tp_percentage = insurer_rate.tp_percentage
                                                else:
                                                    insurer_od_percentage = 0.0
                                                    insurer_net_percentage = 0.0
                                                    insurer_tp_percentage = 0.0
                                                    
                                                coverage = extracted_data.get('coverage_details', {})

                                                policy_od_premium = coverage.get('own_damage', {}).get('premium', 0)
                                                policy_tp_premium = coverage.get('third_party', {}).get('premium', 0)

                                                policy_net_premium = policy_od_premium + policy_tp_premium
                                                policy_gross_premium = extracted_data.get('gross_premium', 0)
                                                    
                                                policy = PolicyDocument.objects.create(
                                                    policy_number=policy_number,
                                                    vehicle_number=vehicle_number,
                                                    holder_name=extracted_data.get('insured_name', ''),
                                                    policy_issue_date=extracted_data.get('issue_date', ''),
                                                    policy_expiry_date=extracted_data.get('expiry_date', ''),
                                                    policy_start_date=extracted_data.get('start_date', ''),
                                                    policy_period=extracted_data.get('policy_period', ''),
                                                    od_premium=policy_od_premium,
                                                    tp_premium=policy_tp_premium,
                                                    policy_premium=policy_gross_premium,
                                                    policy_total_premium=policy_net_premium,
                                                    sum_insured=extracted_data.get('sum_insured', ''),
                                                    insurance_provider=extracted_data.get('insurance_company', ''),
                                                    coverage_details=extracted_data.get('coverage_details', {}),
                                                    vehicle_make=extracted_data.get('vehicle_details', {}).get('make', ''),
                                                    vehicle_model=extracted_data.get('vehicle_details', {}).get('model', ''),
                                                    vehicle_type=extracted_data.get('vehicle_details', {}).get('vehicle_type', ''),
                                                    vehicle_gross_weight=extracted_data.get('vehicle_details', {}).get('vehicle_gross_weight', ''),
                                                    vehicle_manuf_date=extracted_data.get('vehicle_details', {}).get('manufacture_year', ''),
                                                    policy_type=extracted_data.get('additional_details', {}).get('policy_type', ''),
                                                    payment_status=extracted_data.get('additional_details', {}).get('ncb', ''),
                                                    gst=extracted_data.get('gst_premium', ''),
                                                    extracted_text=extracted_data,
                                                    status=6,
                                                    filename=file.filename,
                                                    filepath=file.file_url,
                                                    rm_id=rm_id,
                                                    insurance_company_id=insurance_company_id,
                                                    rm_name=rm_name,
                                                    od_percent=od_percentage,
                                                    tp_percent=tp_percentage,
                                                    net_percent=net_percentage,
                                                    insurer_tp_commission   = insurer_tp_percentage,
                                                    insurer_od_commission   = insurer_od_percentage,
                                                    insurer_net_commission  = insurer_net_percentage,
                                                )
                                                
                                                policy_info = PolicyInfo.objects.create(
                                                    policy_id = policy.id, 
                                                    policy_number = policy.policy_number, 
                                                    policy_issue_date = policy.policy_issue_date, 
                                                    policy_start_date = policy.policy_start_date, 
                                                    policy_expiry_date = policy.policy_expiry_date, 
                                                    insurer_name = policy.insurance_provider, 
                                                    insurance_company = policy.insurance_provider, 
                                                )
                                                
                                                file.policy_id = policy
                                                file.status = 6
                                                file.is_completed = True
                                                file.save()
                                            except Exception as e:
                                                logger.error(f"Error in Creating Policy for extracted_file_id {file.id}, Error:{str(e)}")
                                    except Exception as e:
                                        logger.error(f"Error in fetching policy data for extracted_file_id {file.id}, Error :{str(e)}")
                                        continue
                                else:
                                    logger.error(f"Policy Number or Insurance Company is not found for file_id :{file.id}")
                                    continue
                            except json.JSONDecodeError:
                                logger.error(f"Invalid JSON in chat_response for extratced_file_id {file.id}")
                                continue
                        else:
                            logger.error(f"Unable to create instance of extracted data for extratced_file_id: {file.id}")
                            continue
                    else:
                        logger.error(f"Extracted Data is not found for extracted_file_id:{file.id}")
                        continue
                logger.info(f"Complete CreateNewPolicySinglePolicy Cron Job for extracted_file_ids : {file_ids}")
            else:
                logger.info(f"Do not require processing in CreateNewPolicySinglePolicy .")
        except Exception as e:
            logger.error(f"Unknown error in CreateNewPolicySinglePolicy Cron Job: {str(e)}")
            
class GettingSourceId(CronJobBase):
    RUN_EVERY_MINS = 1
    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)
    code = 'empPortal.getting_source_id'
    
    def do(self):
        try:
            cutoff_time = datetime.strptime('2025-04-24 01:01', '%Y-%m-%d %H:%M')

            files = ExtractedFile.objects.filter(
                source_id__isnull=True,
                is_uploaded=False,
                extracted_at__gte=cutoff_time,
                retry_source_count__lte=2
            )[:10]

            for file in files:
                pdf_path = file.file_path.path
                file.status = 1
                file.save()
                if os.path.exists(pdf_path):
                    try:
                        headers = {
                            'x-api-key': settings.CHATPDF_API_KEY
                        }
                        with open(pdf_path, 'rb') as f:
                            open_files = [('file', (file.filename, f, 'application/pdf'))]
                            response = requests.post(settings.CHATPDF_SOURCE_API_URL, headers=headers, files=open_files)
                            
                        if response.status_code == 200:
                            source_id = response.json().get('sourceId')
                            file.source_id = source_id
                            file.status = 2
                            file.retry_source_count += 1
                            file.is_uploaded = True
                            file.save()
                            
                            logger.info(f"Updated source_id for file ID: {file.id}, filename: {file.filename}, Source ID: {source_id}")
                        else:
                            file.retry_source_count += 1
                            if(file.retry_source_count == 3):
                                file.is_failed = True
                                file.bulk_log_ref.count_error_pdf_files += 1
                            file.save()
                            logger.error(f"Failed to upload extracted_file {file.id}. Status: {response.status_code}, Error: {response.text}")
                            continue
                    except Exception as e:
                        logger.error(f"Error for extracted_file_id: {file.id}, Error: {str(e)}")
                else:
                    logger.error(f"PDF file not found for extracted_file_id: {file.id}")
            logger.info(f"Complete GettingSourceId Cron Job")
        except Exception as e:
            logger.error(f"Unknown Error in GettingSourceId Cron Job: {str(e)}")

class GettingPdfExtractedData(CronJobBase):
    RUN_EVERY_MINS = 1
    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)
    code = 'empPortal.getting_pdf_extracted_data'
    
    def do(self):
        try:
            
            cutoff_time = datetime.strptime('2025-04-24 01:01', '%Y-%m-%d %H:%M')

            files = ExtractedFile.objects.filter(
                source_id__isnull=False,
                is_uploaded=True,
                extracted_at__gte=cutoff_time,
                policy_id__isnull=True,
                retry_chat_response_count__lte=2
            )[:10]
            for file in files:
                if not file.source_id:
                    logger.error(f"No source_id found for file_id {file.id}")
                    continue
                try:
                    file.status = 3
                    file.retry_chat_response_count += 1
                    if(file.retry_chat_response_count == 3):
                        file.is_failed = True
                        file.bulk_log_ref.count_error_pdf_files += 1
                    file.save()
                    headers = {
                        'x-api-key': settings.CHATPDF_API_KEY,
                        "Content-Type": "application/json",
                    }
                    
                    message = chatPdfMessage()
                    data = {
                        'sourceId': file.source_id,
                        'messages': [
                            {
                                'role': "user",
                                'content': message
                            }
                        ]
                    }
                    
                    response = requests.post(
                        settings.CHATPDF_CHAT_API_URL,
                        headers=headers,
                        json=data
                    )
                    
                    logger.info(f"Status Code for Extracting Data for extracted_file_id:{file.id} is {response.status_code}")
                    
                    if response.status_code == 200:
                        result = response.json().get('content')
                        logger.info(f"Extracting Data for extracted_file_id:{file.id} is {result}")
                        
                        if isinstance(result, str):
                            cleaned_result = re.sub(r'```(?:json)?\s*|\s*```', '', result).strip()
                            extracted_data = json.loads(cleaned_result)
                        else:
                            extracted_data = result
                            
                        
                        file.chat_response = extracted_data
                        file.is_extracted = True
                        file.status = 4
                        file.save()
                    else:
                        logger.error(f"ChatPDF API failed for file_id {file.id}. Status: {response.status_code}, Error: {response.text}")
                        continue
                except Exception as e:
                    logger.error(f"Error in api of pdf text extraction for extracted_file_id: {file.id} is {str(e)}")
        except Exception as e:
            logger.error(f"Unknown Error in GettingPdfExtractedData, Error{str(e)}")
            
class CreateNewPolicy(CronJobBase):
    RUN_EVERY_MINS = 1
    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)
    code = 'empPortal.create_new_policy'
    
    def do(self):
        try:
            file_ids = []
            
            cutoff_time = datetime.strptime('2025-04-24 01:01', '%Y-%m-%d %H:%M')

            files = ExtractedFile.objects.filter(policy_id__isnull = True, extracted_at__gte=cutoff_time,retry_creating_policy_count__lte=2,is_extracted=True)[:10]
            for file in files:
                file.status = 5
                file.retry_creating_policy_count += 1
                if(file.retry_creating_policy_count == 3):
                    file.is_failed = True
                    file.bulk_log_ref.count_error_pdf_files += 1
                file.save()
                file_ids.append(file.id)
                extracted_data = file.chat_response
                if extracted_data:
                    if isinstance(extracted_data, str):
                        try:
                            extracted_data = ast.literal_eval(extracted_data)
                            if extracted_data.get('policy_number') and extracted_data.get('insurance_company'):
                                policy_number = extracted_data.get('policy_number', '')
                                vehicle_number = extracted_data.get('vehicle_number', '')
                                bulk_policy_log = file.bulk_log_ref
                                
                                try:
                                    policy_exist = PolicyDocument.objects.filter(policy_number=policy_number).exists()
                                    if policy_exist:
                                        try:
                                            bulk_policy_log.count_uploaded_files += 1
                                            bulk_policy_log.count_duplicate_files += 1
                                            bulk_policy_log.is_processed=True
                                            if(bulk_policy_log.count_uploaded_files >= bulk_policy_log.count_pdf_files):
                                                bulk_policy_log.is_processed=True
                                                bulk_policy_log.status=3
                                            bulk_policy_log.save()
                                            file.status = 7
                                            file.policy_id = policy_exist
                                            file.save()
                                        except Exception as e:
                                            logger.error(f"Error in updating bulk_policy_log in CreateNewPolicy job for extracted_file_id: {file.id}")
                                            continue
                                    else:
                                        try:
                                            rm_id = bulk_policy_log.rm_id
                                            insurance_company_id = bulk_policy_log.insurance_company_id
                                            rm_name = bulk_policy_log.rm_name
                                            commision_rate = commisionRateByMemberId(rm_id)
                                            insurer_rate = insurercommisionRateByMemberId(1)
                                            if commision_rate:
                                                od_percentage = commision_rate.od_percentage
                                                net_percentage = commision_rate.net_percentage
                                                tp_percentage = commision_rate.tp_percentage
                                            else:
                                                od_percentage = 0.0
                                                net_percentage = 0.0
                                                tp_percentage = 0.0
                                                
                                            if insurer_rate:
                                                insurer_od_percentage = insurer_rate.od_percentage
                                                insurer_net_percentage = insurer_rate.net_percentage
                                                insurer_tp_percentage = insurer_rate.tp_percentage
                                            else:
                                                insurer_od_percentage = 0.0
                                                insurer_net_percentage = 0.0
                                                insurer_tp_percentage = 0.0
                                                
                                            coverage = extracted_data.get('coverage_details', {})

                                            policy_od_premium = coverage.get('own_damage', {}).get('premium', 0)
                                            policy_tp_premium = coverage.get('third_party', {}).get('premium', 0)

                                            policy_net_premium = policy_od_premium + policy_tp_premium
                                            policy_gross_premium = extracted_data.get('gross_premium', 0)
                                                
                                            policy = PolicyDocument.objects.create(
                                                policy_number=policy_number,
                                                vehicle_number=vehicle_number,
                                                holder_name=extracted_data.get('insured_name', ''),
                                                policy_issue_date=extracted_data.get('issue_date', ''),
                                                policy_expiry_date=extracted_data.get('expiry_date', ''),
                                                policy_start_date=extracted_data.get('start_date', ''),
                                                policy_period=extracted_data.get('policy_period', ''),
                                                od_premium=policy_od_premium,
                                                tp_premium=policy_tp_premium,
                                                policy_premium=policy_gross_premium,
                                                policy_total_premium=policy_net_premium,
                                                sum_insured=extracted_data.get('sum_insured', ''),
                                                insurance_provider=extracted_data.get('insurance_company', ''),
                                                coverage_details=extracted_data.get('coverage_details', {}),
                                                vehicle_make=extracted_data.get('vehicle_details', {}).get('make', ''),
                                                vehicle_model=extracted_data.get('vehicle_details', {}).get('model', ''),
                                                vehicle_type=extracted_data.get('vehicle_details', {}).get('vehicle_type', ''),
                                                vehicle_gross_weight=extracted_data.get('vehicle_details', {}).get('vehicle_gross_weight', ''),
                                                vehicle_manuf_date=extracted_data.get('vehicle_details', {}).get('manufacture_year', ''),
                                                policy_type=extracted_data.get('additional_details', {}).get('policy_type', ''),
                                                payment_status=extracted_data.get('additional_details', {}).get('ncb', ''),
                                                gst=extracted_data.get('gst_premium', ''),
                                                extracted_text=extracted_data,
                                                status=6,
                                                bulk_log_id=bulk_policy_log.id,
                                                filename=file.filename,
                                                filepath=file.file_url,
                                                rm_id=rm_id,
                                                insurance_company_id=insurance_company_id,
                                                rm_name=rm_name,
                                                od_percent=od_percentage,
                                                tp_percent=tp_percentage,
                                                net_percent=net_percentage,
                                                insurer_tp_commission   = insurer_tp_percentage,
                                                insurer_od_commission   = insurer_od_percentage,
                                                insurer_net_commission  = insurer_net_percentage,
                                            )
                                            
                                            policy_info = PolicyInfo.objects.create(
                                                policy_id = policy.id, 
                                                policy_number = policy.policy_number, 
                                                policy_issue_date = policy.policy_issue_date, 
                                                policy_start_date = policy.policy_start_date, 
                                                policy_expiry_date = policy.policy_expiry_date, 
                                                insurer_name = policy.insurance_provider, 
                                                insurance_company = policy.insurance_provider, 
                                            )
                                            
                                            bulk_policy_log.count_uploaded_files += 1
                                            if(bulk_policy_log.count_uploaded_files >= bulk_policy_log.count_pdf_files):
                                                bulk_policy_log.is_processed=True
                                                bulk_policy_log.status=3
                                            bulk_policy_log.save()
                                            
                                            file.policy_id = policy
                                            file.status = 6
                                            file.save()
                                        except Exception as e:
                                            logger.error(f"Error in Creating Policy for extracted_file_id {file.id}, Error:{str(e)}")
                                except Exception as e:
                                    logger.error(f"Error in fetching policy data for extracted_file_id {file.id}, Error :{str(e)}")
                                    continue
                            else:
                                logger.error(f"Policy Number or Insurance Company is not found for file_id :{file.id}")
                                continue
                        except json.JSONDecodeError:
                            logger.error(f"Invalid JSON in chat_response for extratced_file_id {file.id}")
                            continue
                    else:
                        logger.error(f"Unable to create instance of extracted data for extratced_file_id: {file.id}")
                        continue
                else:
                    logger.error(f"Extracted Data is not found for extracted_file_id:{file.id}")
                    continue
            logger.info(f"Complete CreateNewPolicy Cron Job for extracted_file_ids : {file_ids}")
        except Exception as e:
            logger.error(f"Unknown error in CreateNewPolicy Cron Job: {str(e)}")
            
class updatePolicyInfoByPolicyNumber(CronJobBase):
    RUN_EVERY_MINS = 1
    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)
    code = 'empPortal.updatePolicyInfo'
    
    def do(self):
        print("------ Policy Info Update Cron Started ------")

        # Step 1: Build policy_number -> policy_id mapping
        policy_mapping = dict(
            PolicyDocument.objects.filter(status=6)
            .values_list('policy_number', 'id')
        )
        print(f"Loaded {len(policy_mapping)} active policies.")

        updated_counts = {
            'InsurerPaymentDetails': 0,
            'AgentPaymentDetails': 0,
            'FranchisePayment': 0,
            'PolicyVehicleInfo': 0,
            'PolicyInfo': 0,
        }

        # Step 2: Update InsurerPaymentDetails
        for insurer_detail in InsurerPaymentDetails.objects.filter(policy_id__isnull=True, policy_number__isnull=False):
            policy_id = policy_mapping.get(insurer_detail.policy_number)
            if policy_id:
                insurer_detail.policy_id = policy_id
                insurer_detail.save()
                updated_counts['InsurerPaymentDetails'] += 1

        # Step 3: Update AgentPaymentDetails
        for agent_detail in AgentPaymentDetails.objects.filter(policy_id__isnull=True, policy_number__isnull=False):
            policy_id = policy_mapping.get(agent_detail.policy_number)
            if policy_id:
                agent_detail.policy_id = policy_id
                agent_detail.save()
                updated_counts['AgentPaymentDetails'] += 1

        # Step 4: Update FranchisePayment
        for franchise_detail in FranchisePayment.objects.filter(policy_id__isnull=True, policy_number__isnull=False):
            policy_id = policy_mapping.get(franchise_detail.policy_number)
            if policy_id:
                franchise_detail.policy_id = policy_id
                franchise_detail.save()
                updated_counts['FranchisePayment'] += 1

        # Step 5: Update PolicyVehicleInfo
        for vehicle_detail in PolicyVehicleInfo.objects.filter(policy_id__isnull=True, policy_number__isnull=False):
            policy_id = policy_mapping.get(vehicle_detail.policy_number)
            if policy_id:
                vehicle_detail.policy_id = policy_id
                vehicle_detail.save()
                updated_counts['PolicyVehicleInfo'] += 1

        # Step 6: Update PolicyInfo
        for info_detail in PolicyInfo.objects.filter(policy_id__isnull=True, policy_number__isnull=False):
            policy_id = policy_mapping.get(info_detail.policy_number)
            if policy_id:
                info_detail.policy_id = policy_id
                info_detail.save()
                updated_counts['PolicyInfo'] += 1

        # Final Logs
        print("------ Cron Job Completed ------")
        for model_name, count in updated_counts.items():
            print(f"Updated {count} records in {model_name}.")

        print("--------------------------------")
        