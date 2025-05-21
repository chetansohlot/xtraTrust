from .models import UploadedZip, FileAnalysis, ExtractedFile, BulkPolicyLog, Commission, PolicyDocument, UnprocessedPolicyFiles, ChatGPTLog, UploadedExcel
from .models import PolicyInfo, PolicyVehicleInfo, AgentPaymentDetails, InsurerPaymentDetails, FranchisePayment
from .models import FranchisePaymentLog, PolicyInfoLog, PolicyVehicleInfoLog, AgentPaymentDetailsLog, InsurerPaymentDetailsLog
import django, dramatiq, fitz, os, zipfile, requests, re, json, traceback, time, logging, shutil
from django.conf import settings
from django.utils import timezone
from django.utils.timezone import now
from django_q.tasks import async_task
OPENAI_API_KEY = settings.OPENAI_API_KEY
from django.db.models import F
from .utils import getUserNameByUserId, commisionRateByMemberId, insurercommisionRateByMemberId, to_int, chatPdfMessage
from django.core.exceptions import ObjectDoesNotExist
from django.utils.encoding import filepath_to_uri
import pandas as pd

logging.getLogger('faker').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

def create_bulk_log(file_id):
    zip_instance = UploadedZip.objects.get(id=file_id)
    
    try:
        bulk_log = BulkPolicyLog.objects.create(
            camp_name=zip_instance.campaign_name,
            file_name=zip_instance.file.name,
            count_total_files=zip_instance.total_files,
            count_not_pdf=zip_instance.non_pdf_files_count,
            count_pdf_files=zip_instance.pdf_files_count,
            file_url=zip_instance.file.url,
            count_error_pdf_files=0,
            count_error_process_pdf_files=0,
            count_uploaded_files=0,
            count_duplicate_files=0,
            rm_id=zip_instance.rm_id,
            created_by=zip_instance.created_by.id,
            status=1,
        )
        
        zip_instance.bulk_log = bulk_log
        zip_instance.save()
        
        async_task('empPortal.tasks.process_zip_file', file_id)
    except Exception as e:
        logger.error(f"Failed to insert entry in BulkPolicyLog for UploadedZipId :{file_id} -> error :{str(e)}" )
    
def process_zip_file(zip_id):
    try:
        zip_instance = UploadedZip.objects.filter(is_processed=0,id=zip_id).first()
        if zip_instance.exists():
            pdf_file_ids = []
            zip_path = zip_instance.file.path
            
            extract_dir = os.path.join(settings.MEDIA_ROOT, 'extracted', str(zip_id))
            if os.path.exists(extract_dir):
                shutil.rmtree(extract_dir)

            # Now create a fresh folder
            os.makedirs(extract_dir, exist_ok=True)

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

            for filename in os.listdir(extract_dir):
                if not filename.lower().endswith('.pdf'):
                    continue  # Skip non-PDFs

                file_path = os.path.join(extract_dir, filename)
                relative_path = os.path.relpath(file_path, settings.MEDIA_ROOT)
                file_url = filepath_to_uri(os.path.join(settings.MEDIA_URL, relative_path))

                try:
                    extracted = ExtractedFile.objects.create(
                        zip_ref=zip_instance,
                        file_path=file_path,
                        filename=filename,
                        file_url=file_url
                    )
                    
                    # only append if created successfully
                    pdf_file_ids.append(extracted.id)
                except Exception as e:
                    logger.error(f"Error processing file_path {file_path}: {str(e)}")
                    continue
                
            zip_instance.is_processed = True
            zip_instance.save()
            
            bulk_log = zip_instance.bulk_log
            bulk_log.status = 2
            bulk_log.save()
            
            # upload extracted files to policy document 
            async_task('empPortal.tasks.create_policy_documents_bulk', pdf_file_ids)
        else:
            logger.error(f"Zip File is not found for zip_id: {zip_id} ")
    except Exception as e:
        logger.error(f"Unknown Error in process_zip_file")
    

def create_policy_documents_bulk(file_ids):
    for file_id in file_ids:
        try:
            create_policy_document(file_id)  # call your create_policy_document function
            # time.sleep(6)  # Delay between jobs
        except Exception as e:
            # Handle errors per file if needed
            logger.error(f"Error in create_policy_documents_bulk for ExtractedFileId {file_id}: {str(e)}")
    
    logger.info(f"create_policy_documents_bulk is successfully completed for ExtractedFileIds {file_ids}")
    
def create_policy_document(file_id):
    try:
        file_obj = ExtractedFile.objects.filter(id=file_id,is_extracted=0).first()
        rm_id = file_obj.zip_ref.bulk_log.rm_id
        bulk_log_id = file_obj.zip_ref.bulk_log.id
        rm_name = getUserNameByUserId(rm_id) if rm_id else None
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
            
        try:
            policy = PolicyDocument.objects.create(
                filename=file_obj.filename,
                filepath=file_obj.file_url,
                rm_id=rm_id,
                rm_name=rm_name,
                od_percent=od_percentage,
                tp_percent=tp_percentage,
                net_percent=net_percentage,
                insurer_tp_commission   = insurer_tp_percentage,
                insurer_od_commission   = insurer_od_percentage,
                insurer_net_commission  = insurer_net_percentage,
                status=0,
                bulk_log_id=bulk_log_id
            )
            
            file_obj.policy = policy
            file_obj.is_extracted = 1
            file_obj.save()
            async_task('empPortal.tasks.upload_pdf_store_source_id', file_obj.id)
        except Exception as e:
            logger.error(f"Error in create_policy_document for ExtractedFile {file_id}: {str(e)}")
            
        # time.sleep(6)  
        # async_task('empPortal.tasks.extract_pdf_text_task', file_obj.id)
    except Exception as e:
        logger.error(f"Unknown Error in create_policy_document for ExtractedFileId {file_id}: {str(e)}")
        
def reprocessFiles(file_id):

    try:
        file_data = PolicyDocument.objects.get(id=file_id)
        file_status = file_data.status
        if file_status != 6:
            file_obj = ExtractedFile.objects.filter(policy_id=file_id).last()
            time.sleep(6)
            async_task('empPortal.tasks.upload_pdf_store_source_id', file_obj.id)
               
    except PolicyDocument.DoesNotExist:
        print(f"File with ID {file_id} not found in Policy Details")
    
    except FileAnalysis.DoesNotExist:
        print(f"File with ID {file_id} not found in analysing")
        
    except ExtractedFile.DoesNotExist:
        print(f"File with ID {file_id} not found in extraction")
 
def upload_pdf_store_source_id(file_id):
    try:
        file_obj = ExtractedFile.objects.get(id=file_id)
        if file_obj:
            pdf_path = file_obj.file_path.path
            if file_obj.source_id: 
                async_task('empPortal.tasks.process_chatpdf_text_task', file_obj.id)
            else:
                if os.path.exists(pdf_path):
                    
                    headers = {
                        'x-api-key': 'sec_m1M7LeA6FHM4Spy0vhzcBC65fSPOvims'
                    }

                    with open(pdf_path, 'rb') as f:
                        files = [('file', (file_obj.filename, f, 'application/pdf'))]
                        response = requests.post('https://api.chatpdf.com/v1/sources/add-file', headers=headers, files=files)

                    if response.status_code == 200:
                        source_id = response.json().get('sourceId')
                        file_obj.source_id = source_id
                        file_obj.is_uploaded = True
                        file_obj.save()
                        
                        async_task('empPortal.tasks.process_chatpdf_text_task', file_obj.id)
                        logger.info(f"Uploaded {file_obj.filename} to ChatPDF. Source ID: {source_id}")
                    else:
                        logger.error(f"Failed to upload {file_obj.filename}. Status: {response.status_code}, Error: {response.text}")
                else:
                    logger.error(f"PDF file not found for file_id: {file_id}")
        else:
            logger.error(f"upload_pdf_store_source_id file_obj with ID {file_id} not found.")
    except ExtractedFile.DoesNotExist:
        logger.error(f"ExtractedFile with ID {file_id} not found.")
    except Exception as e:
        logger.error(f"Error in upload_pdf_store_source_id for file_id {file_id}: {str(e)}")

def process_chatpdf_text_task(file_id):
    result = process_text_with_chatpdf_api(file_id)
    logger.info(f"process_chatpdf_text_task ChatPDF processing result for file_id {file_id}")

def process_text_with_chatpdf_api(file_id):
    try:
        file_obj = ExtractedFile.objects.get(id=file_id)
        policy_obj = file_obj.policy

        if not file_obj.source_id:
            logger.error(f"No source_id found for file_id {file_id}")
            return json.dumps({"error": "No source_id found."}, indent=4)

        headers = {
            'x-api-key': 'sec_m1M7LeA6FHM4Spy0vhzcBC65fSPOvims',
            "Content-Type": "application/json",
        }

        message = chatPdfMessage()
        
        data = {
            'sourceId': file_obj.source_id,
            'messages': [
                {
                    'role': "user",
                    'content': message
                }
            ]
        }

        response = requests.post(
            'https://api.chatpdf.com/v1/chats/message',
            headers=headers,
            json=data
        )
        
        logger.info(f"Result exists. Started second data... {response.status_code}")

        if response.status_code == 200:
            result = response.json().get('content')
            if isinstance(result, str):
                cleaned_result = re.sub(r'```(?:json)?\s*|\s*```', '', result).strip()
                extracted_data = json.loads(cleaned_result)
            else:
                extracted_data = result
            # Save result to both ExtractedFile and PolicyDocument
            file_obj.chat_response = extracted_data
            file_obj.save()
            bulk_log_obj =BulkPolicyLog.objects.get(id=policy_obj.bulk_log_id)
            try:
                logger.info("Starting result processing...")

                if result:
                    logger.info("Result exists. Processing data...")

                    if extracted_data.get('policy_number') and extracted_data.get('insurance_company'):
                        policy_number = extracted_data.get('policy_number', '')
                        vehicle_number = extracted_data.get('vehicle_number', '')
                        # Assign extracted values to PolicyDocument fields
                        if PolicyDocument.objects.filter(policy_number=policy_number, vehicle_number=vehicle_number).exists():
                            policy_obj.status = 7
                            policy_obj.save()
                            
                            bulk_log_obj.count_duplicate_files += 1
                            bulk_log_obj.count_uploaded_files += 1
                            bulk_log_obj.save()
                            
                            if bulk_log_obj.count_uploaded_files == bulk_log_obj.count_pdf_files:
                                bulk_log_obj.status = 3
                                bulk_log_obj.save()
                        else:
                            policy_obj.policy_number = policy_number
                            policy_obj.vehicle_number = vehicle_number
                            policy_obj.holder_name = extracted_data.get('insured_name', '')
                            policy_obj.policy_issue_date = extracted_data.get('issue_date', '')
                            policy_obj.policy_expiry_date = extracted_data.get('expiry_date', '')
                            policy_obj.policy_start_date = extracted_data.get('start_date', '')
                            policy_obj.policy_period = extracted_data.get('policy_period', '')
                            policy_obj.policy_premium = extracted_data.get('gross_premium', '')
                            policy_obj.policy_total_premium = extracted_data.get('net_premium', '')
                            policy_obj.sum_insured = extracted_data.get('sum_insured', '')
                            policy_obj.insurance_provider = extracted_data.get('insurance_company', '')
                            policy_obj.coverage_details = extracted_data.get('coverage_details', {})
                            policy_obj.vehicle_make = extracted_data.get('vehicle_details', {}).get('make', '')
                            policy_obj.vehicle_model = extracted_data.get('vehicle_details', {}).get('model', '')
                            policy_obj.vehicle_type = extracted_data.get('vehicle_details', {}).get('vehicle_type', '')
                            policy_obj.vehicle_gross_weight = extracted_data.get('vehicle_details', {}).get('vehicle_gross_weight', '')
                            policy_obj.vehicle_manuf_date = extracted_data.get('vehicle_details', {}).get('manufacture_year', '')
                            policy_obj.policy_type = extracted_data.get('additional_details', {}).get('policy_type', '')
                            policy_obj.payment_status = extracted_data.get('additional_details', {}).get('ncb', '')
                            policy_obj.gst = extracted_data.get('gst_premium', '')
                            policy_obj.od_premium = extracted_data.get('coverage_details', {}).get('own_damage', {}).get('premium', '')
                            policy_obj.tp_premium = extracted_data.get('coverage_details', {}).get('third_party', {}).get('premium', '')

                            policy_obj.extracted_text = extracted_data
                            policy_obj.status = 6  # processing complete
                            policy_obj.save()
                            
                            
                            bulk_log_obj.count_uploaded_files += 1
                            bulk_log_obj.save()
                            if bulk_log_obj.count_uploaded_files == bulk_log_obj.count_pdf_files:
                                bulk_log_obj.status = 3
                                bulk_log_obj.save()
                    else:
                        
                        policy_obj.status = 6  # processing complete
                        policy_obj.save()
                        logger.warning("Policy Number or insurance_company is not found.")
                else:
                    logger.warning("No result to process.")
            except Exception as e:
                logger.error(f"Exception occurred: {e}")

            logger.info(f"Processed ChatPDF response for file_id {file_id}, policy_id {policy_obj.id}")

            return result

        else:
            logger.error(f"ChatPDF API failed for file_id {file_id}. Status: {response.status_code}, Error: {response.text}")
            return json.dumps({"error": f"API Error: {response.status_code}", "details": response.text}, indent=4)

    except ExtractedFile.DoesNotExist:
        logger.error(f"ExtractedFile with ID {file_id} not found.")
    except PolicyDocument.DoesNotExist:
        logger.error(f"PolicyDocument not found for file_id {file_id}")
    except Exception as e:
        logger.error(f"Error in process_text_with_chatpdf_api for file_id {file_id}: {str(e)}")

def extract_pdf_text_task(file_id):
    try:
        file_obj = ExtractedFile.objects.get(id=file_id)
    except ExtractedFile.DoesNotExist:
        logger.error(f"ExtractedFile with ID {file_id} not found.")
        return

    policy_obj = file_obj.policy
    policy_obj.status = 1
    policy_obj.save()

    pdf_path = file_obj.file_path.path if hasattr(file_obj.file_path, "path") else file_obj.file_path
    text = extract_text_from_pdf(pdf_path)
    try:
        file_analysis = FileAnalysis.objects.create(
            zip=file_obj.zip_ref,
            extracted_file=file_obj,
            policy=policy_obj,
            filename=file_obj.filename,
            extracted_text=text,
        )
    except Exception as e:
        logger.error(f"Error in file analysing file_id {file_id} : {str(e)}")

    try:
        if "Error" in text:
            BulkPolicyLog.objects.filter(id=file_obj.zip_ref.bulk_log.id).update(
                count_error_pdf_files=F('count_error_pdf_files') + 1
            )
            try:
                UnprocessedPolicyFiles.objects.create(
                    policy_document=policy_obj.id,
                    doc_name=file_obj.filename,
                    bulk_log_id=policy_obj.bulk_log_id,
                    file_path=policy_obj.filepath,
                    status=1,  # pending
                )
            except Exception as e:
                logger.error(f"Error in Unprocessing File file_id {file_id} : {str(e)}")
            file_analysis.status = 2  #failed in extarction
            file_analysis.save()
            
        else:
            file_analysis.status = 1    #extraction complete
            file_analysis.save()

            file_obj.content = text.strip()
            file_obj.is_extracted = True
            file_obj.save()

            policy_obj.status = 2
            policy_obj.save()

            # Proceed to AI processing task (uncomment if needed)
            async_task('empPortal.tasks.process_text_from_chatgpt', file_analysis.id)


    except Exception as e:
        BulkPolicyLog.objects.filter(id=file_obj.zip_ref.bulk_log.id).update(
            count_error_pdf_files=F('count_error_pdf_files') + 1
        )
        try:
            UnprocessedPolicyFiles.objects.create(
                policy_document=policy_obj.id,
                doc_name=file_obj.filename,
                bulk_log_id=policy_obj.bulk_log_id,
                file_path=policy_obj.filepath,
                status=1,  # pending
            )
        except Exception as e:
            logger.error(f"Error in Unprocessing File file_id {file_id} : {str(e)}")
        file_analysis.status = 2  #failed in extarction
        file_analysis.save()
   
def extract_text_from_pdf(pdf_path):
    try:
        doc = fitz.open(pdf_path)
        text = "\n".join(page.get_text("text") for page in doc)
        return text
    except Exception as e:
        logger.debug(f"Error extracting text: {e}")
        return f"Error extracting text: {e}"

def handle_ai_processing_failure(file_obj, policy_obj):
    try:
        BulkPolicyLog.objects.filter(id=file_obj.zip_ref.bulk_log.id).update(
            count_error_pdf_files=F('count_error_pdf_files') + 1
        )
        try:
            UnprocessedPolicyFiles.objects.create(
                policy_document=policy_obj.id,
                doc_name=file_obj.filename,
                bulk_log_id=policy_obj.bulk_log_id,
                file_path=policy_obj.filepath,
                status=2,  # error at AI Processing
            )
        except Exception as e:
            logger.error(f"error in ai_processing policy_id {policy_obj.id}")   

        file_obj.status = 3  # failed in AI Processing
        file_obj.save()
    except Exception as e:
        logger.error(f"Secondary error while logging AI failure: {e}")
        traceback.print_exc()

def process_text_from_chatgpt(file_id):
    try:
        file_obj = FileAnalysis.objects.get(id=file_id)
        policy_obj = file_obj.policy

        # Mark as processing
        policy_obj.status = 3
        policy_obj.save()

        response_json = process_text_with_chatgpt(file_obj.extracted_text)

        if hasattr(response_json, "error"):
            file_obj.gpt_response = response_json
            file_obj.save()
            handle_ai_processing_failure(file_obj, policy_obj)
        else:
            # Save GPT response and mark successful
            file_obj.gpt_response = response_json
            file_obj.status = 4
            file_obj.save()

            policy_obj.status = 4
            policy_obj.extracted_text = response_json
            policy_obj.save()

            async_task('empPortal.tasks.update_policy_data', file_id)

    except FileAnalysis.DoesNotExist:
        logger.error(f"FileAnalysis with ID {file_id} not found.")
    except Exception as e:
        logger.error(f"Error in PDF processed with AI: {e}")
        # traceback.print_exc()
        if 'file_obj' in locals() and 'policy_obj' in locals():
            handle_ai_processing_failure(file_obj, policy_obj)

def process_text_with_chatgpt(text):

    prompt = f"""
    Convert the following insurance document text into a structured JSON format without any extra comments. Ensure that numerical values (like premiums and sum insured) are **only numbers** without extra text.  if godigit replace the amount of od and tp from one another 

    ```
    {text}
    ```

    The JSON should have this structure:
    
    {{
        "policy_number": "XXXXXX/XXXXX",   # complete policy number if insurance_company is godigit policy number is 'XXXXXX / XXXXX' in this format   e
        "vehicle_number": "XXXXXXXXXX",
        "insured_name": "XXXXXX",
        "issue_date": "YYYY-MM-DD H:i:s",     
        "start_date": "YYYY-MM-DD H:i:s",
        "expiry_date": "YYYY-MM-DD H:i:s",
        "gross_premium": XXXX,    
        "net_premium": XXXX,
        "gst_premium": XXXX,
        "sum_insured": XXXX,
        "policy_period": "XX Year(s)",
        "insurance_company": "XXXXX",
        "coverage_details": {{
            "own_damage": {{
                "premium": XXXX,
                "additional_premiums": XXXX,
                "addons": {{
                    "addons": [
                        {{ "name": "XXXX", "amount": XXXX }},
                        {{ "name": "XXXX", "amount": XXXX }}
                    ],
                    "discounts": [
                        {{ "name": "XXXX", "amount": XXXX }},
                        {{ "name": "XXXX", "amount": XXXX }}
                    ]
                }}
            }},
            "third_party": {{
                "premium": XXXX,
                "additional_premiums": XXXX,
                "addons": {{
                    "addons": [
                        {{ "name": "XXXX", "amount": XXXX }},
                        {{ "name": "XXXX", "amount": XXXX }}
                    ],
                    "discounts": [
                        {{ "name": "XXXX", "amount": XXXX }},
                        {{ "name": "XXXX", "amount": XXXX }}
                    ]
                }}
            }}
        }},
        "vehicle_details": {{
            "make": "XXXX",
            "model": "XXXX",
            "variant": "XXXX",
            "registration_year": YYYY,
            "manufacture_year": YYYY,
            "engine_number": "XXXXXXXXXXXX",
            "chassis_number": "XXXXXXXXXXXX",
            "fuel_type": "XXXX",     # diesel/petrol/cng/lpg/ev 
            "cubic_capacity": XXXX,  
            "seating_capacity": XXXX,  
            "vehicle_gross_weight": XXXX,   # in kg
            "vehicle_type": "XXXX XXXX",    # private / commercial
            "commercial_vehicle_detail": "XXXX XXXX"    
        }},
        "additional_details": {{
            "policy_type": "XXXX",        # motor stand alone policy/ motor third party liablity policy / motor package policy   only in these texts
            "ncb": XX,     # in percentage
            "addons": ["XXXX", "XXXX"], 
            "previous_insurer": "XXXX",
            "previous_policy_number": "XXXX"
        }},
        "contact_information": {{
            "address": "XXXXXX",
            "phone_number": "XXXXXXXXXX",
            "email": "XXXXXX",
            "pan_no": "XXXXX1111X",
            "aadhar_no": "XXXXXXXXXXXX"
        }}
    }}
    
    If some details are missing, leave them as blank.
    """

    api_url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }

    data = {
        "model": "gpt-4o",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0
    }

    try:
        log_entry = ChatGPTLog.objects.create(
            prompt=prompt,
            created_at=now()
        )
    except:
        logger.error(f"Error In ChatGPT logentry")
  
    try:
        response = requests.post(api_url, json=data, headers=headers)

        if hasattr(response, "status_code"):
            log_entry.status_code = response.status_code
            
        if hasattr(response, "status_code") and response.status_code == 200:

            result = response.json()
            raw_output = result["choices"][0]["message"]["content"].strip()
            
            try:
                clean_json = re.sub(r"```json\n|\n```|```", "", raw_output).strip()
                
                parsed_json = json.loads(clean_json)
                log_entry.response = json.dumps(parsed_json, indent=4)
                log_entry.is_successful = True
                log_entry.save()
                return parsed_json
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error {str(e)}")
                log_entry.response = raw_output
                log_entry.error_message = f"JSON decode error: {str(e)}"
                log_entry.save()
                
                return json.dumps({
                    "error": "JSON decode error",
                    "raw_output": raw_output,
                    "details": str(e)
                }, indent=4)
        else:
            log_entry.error_message = response.text
            log_entry.save()
            return json.dumps({"error": f"API Error: {response.status_code}", "details": response.text}, indent=4)
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed ,details: {str(e)}")
        
        log_entry.error_message = str(e)
        log_entry.save()
        
        return json.dumps({"error": "Request failed", "details": str(e)}, indent=4)

def update_policy_data(file_id):
    try:
        file_obj = FileAnalysis.objects.get(id=file_id)
        policy_obj = file_obj.policy
        policy_obj.status = 5
        policy_obj.save()
        bulk_log = file_obj.zip.bulk_log
        processed_text = file_obj.gpt_response or {}
        duplicate_files = 0
        uploaded_files = 0

        if not isinstance(processed_text, dict):
            processed_text = json.loads(processed_text)

        policy_number = processed_text.get("policy_number")
        if not policy_number:
            policy_obj.status = 4
            policy_obj.save()
            raise ValueError("Policy number is missing in processed_text.")
        else:
            # Check for duplicates
            if PolicyDocument.objects.filter(policy_number=policy_number).exists():
                bulk_log.count_duplicate_files += 1
                bulk_log.save()
                
                policy_obj.status = 7
                policy_obj.save()
                bulk_log.count_uploaded_files += 1
                bulk_log.save()
                if bulk_log.count_uploaded_files == bulk_log.count_pdf_files:
                    bulk_log.status = 3
                    bulk_log.save()
            else:
                try:
                    
                    vehicle_number = re.sub(r"[^a-zA-Z0-9]", "", processed_text.get("vehicle_number", ""))

                    coverage_details = processed_text.get("coverage_details", [{}])
                    if isinstance(coverage_details, list) and coverage_details:
                        first_coverage = coverage_details[0]
                    elif isinstance(coverage_details, dict):
                        first_coverage = coverage_details
                    else:
                        first_coverage = {}

                    od_premium = first_coverage.get('own_damage', {}).get('premium', 0)
                    tp_premium = first_coverage.get('third_party', {}).get('premium', 0)

                    policy_doc = policy_obj
                
                    policy_doc.insurance_provider = processed_text.get("insurance_company", "")
                    policy_doc.vehicle_number = vehicle_number
                    policy_doc.policy_number = policy_number
                    policy_doc.policy_period = processed_text.get("policy_period", "")
                    policy_doc.holder_name = processed_text.get("insured_name", "")
                    policy_doc.policy_total_premium = processed_text.get("gross_premium", 0)
                    policy_doc.policy_premium = processed_text.get("net_premium", 0)
                    policy_doc.sum_insured = processed_text.get("sum_insured", 0)
                    policy_doc.coverage_details = coverage_details
                    policy_doc.policy_issue_date = processed_text.get("issue_date", "")
                    policy_doc.policy_expiry_date = processed_text.get("expiry_date","")
                    policy_doc.policy_start_date = processed_text.get("start_date","")
                    policy_doc.payment_status = 'Confirmed'
                    policy_doc.policy_type = processed_text.get('additional_details', {}).get('policy_type', "")
                    vehicle_details = processed_text.get('vehicle_details', {})
                    policy_doc.vehicle_type = vehicle_details.get('vehicle_type', "")
                    policy_doc.vehicle_make = vehicle_details.get('make', "")
                    policy_doc.vehicle_model = vehicle_details.get('model', "")
                    policy_doc.vehicle_gross_weight = vehicle_details.get('vehicle_gross_weight', "")
                    policy_doc.vehicle_manuf_date = vehicle_details.get('registration_year', "")
                    policy_doc.gst = processed_text.get('gst_premium', 0)
                    policy_doc.od_premium = od_premium
                    policy_doc.tp_premium = tp_premium
                    policy_doc.status = 6
                    policy_doc.save()
                    # Update Bulk Log
                    bulk_log.count_uploaded_files += 1
                    bulk_log.save()
                    if bulk_log.count_uploaded_files == bulk_log.count_pdf_files:
                        bulk_log.status = 3
                        bulk_log.save()
                except Exception as e:
                    logger.error(f"Error in Policy Update for policy_id {policy_obj.id}")
            

    except FileAnalysis.DoesNotExist:
        logger.error(f"File not found with the given ID")
        return json.dumps({"error": "File not found with the given ID."}, indent=4)
    except ObjectDoesNotExist as e:
        logger.error(f"Object not found Error: {str(e)}")
        return json.dumps({"error": "Object not found", "details": str(e)}, indent=4)
    except ValueError as ve:
        logger.error(f"Value error: {str(ve)}")
        return json.dumps({"error": "Value error", "details": str(ve)}, indent=4)
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in GPT response for policy_id : {policy_obj.id}")
        return json.dumps({"error": "Invalid JSON in GPT response"}, indent=4)
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed for policy_id :{policy_obj.id} : error:{str(e)}")
        return json.dumps({"error": "Request failed", "details": str(e)}, indent=4)
    except Exception as e:
        logger.error(f"Unexpected error for policy_id :{policy_obj.id} : error:{str(e)}")
        return json.dumps({"error": "Unexpected error", "details": str(e)}, indent=4)
    
def handle_failure(task):
    attempts = task.attempt_count if hasattr(task, 'attempt_count') else 'Unknown'
    task_name = task.name if hasattr(task, 'name') else 'Unknown Task'
    task_id = task.id if hasattr(task, 'id') else 'No ID'
    if task.get('success') is False:
        logger.error(f"Task {task_id} named {task_name} failed after {attempts}")
        
def updateBulkPolicies(file_id):
    try:
        excel_instance = UploadedExcel.objects.get(id=file_id)
        file_path = excel_instance.file.path

        df = pd.read_excel(file_path)
        errors = []
        valid_count = 0
        invalid_count = 0
        
        if 'policy_number' not in df.columns:
            excel_instance.is_processed = True
            excel_instance.error = "'policy_number' column not found."
            excel_instance.save()
            logger.error(f"'policy_number' column not found. {excel_instance.id}")
        else:
            for index, row in df.iterrows():
                policy_number = str(row.get('policy_number', '')).strip()
                if policy_number:
                    try:
                        policy = PolicyDocument.objects.get(policy_number=policy_number)
                        excel_instance.valid_rows += 1  
                        async_task('empPortal.tasks.create_or_update_policyInfo',index,row,file_id,policy_number,policy)
                    except PolicyDocument.DoesNotExist:
                        excel_instance.invalid_rows += 1
                        logger.error(f"Row {index + 2}: Policy not found in PolicyDocument: {policy_number}")
                        continue
                        
                    except Exception as e: 
                        logger.error(f"Row {index + 2}: Error - {str(e)}")
                        continue
                        
                else:
                    logger.error(f"Row {index + 2}: Missing policy number.")
                    continue
                
        # Update processing status
        excel_instance.is_processed = True
        excel_instance.save()

    except Exception as e:
        logger.error(f"Error: {str(e)}")
    
def update_field(instance, field, value):
    if pd.notna(value) and (str(value).strip() != '' or str(value).strip() != None):
        return setattr(instance, field, value)
                
def create_or_update_policyInfo(index,row,file_id,policy_number,policy):
    try:
        excel_instance = UploadedExcel.objects.get(id=file_id)
        policy_info, created = PolicyInfo.objects.get_or_create(policy_number=policy_number)
        if created:
            action = 'Insert'
            logger.info(f"Row {index + 2}: Created new PolicyInfo for policy_number: {policy_number}")
        else:
            action = 'Update'
            logger.info(f"Row {index + 2}: Updated existing PolicyInfo for policy_number: {policy_number}")

        # Basic Policy
        update_field(policy_info, 'policy_issue_date', row.get('policy_issue_date'))
        update_field(policy_info, 'policy_start_date', row.get('policy_start_date'))
        update_field(policy_info, 'policy_expiry_date', row.get('policy_end_date'))
        update_field(policy_info, 'insurer_name', row.get('insured_name'))
        update_field(policy_info, 'insured_mobile', to_int(row.get('insured_mobile')))
        update_field(policy_info, 'insured_email', row.get('insured_email'))
        update_field(policy_info, 'insured_address', row.get('insured_address'))
        update_field(policy_info, 'insured_pan', row.get('insured_pan'))
        update_field(policy_info, 'insured_aadhaar', to_int(row.get('insured_aadhaar')))
        update_field(policy_info, 'branch_name', row.get('branch_name'))
        update_field(policy_info, 'policy_type', row.get('policy_type'))
        update_field(policy_info, 'policy_plan', row.get('policy_plan'))
        update_field(policy_info, 'sum_insured', to_int(row.get('sum_insured')))
        update_field(policy_info, 'od_premium', to_int(row.get('od_premium')))
        update_field(policy_info, 'tp_premium', to_int(row.get('tp_premium')))
        update_field(policy_info, 'pa_count', to_int(row.get('pa_count')))
        update_field(policy_info, 'pa_amount', to_int(row.get('pa_amount')))
        update_field(policy_info, 'driver_count', to_int(row.get('driver_count')))
        update_field(policy_info, 'driver_amount', to_int(row.get('driver_amount')))
        update_field(policy_info, 'fuel_type', row.get('fuel_type'))
        update_field(policy_info, 'be_fuel_amount', to_int(row.get('be_fuel_amount')))
        update_field(policy_info, 'gross_premium', to_int(row.get('gross_premium')))
        update_field(policy_info, 'net_premium', to_int(row.get('net_premium')))
        update_field(policy_info, 'bqp', row.get('bqp'))
        update_field(policy_info, 'pos_name', row.get('pos_name'))
        update_field(policy_info, 'referral_by', row.get('referral_by'))
        policy_info.save()
        
        logs = PolicyInfoLog.objects.create(
            policy_info_id= policy_info.id,
            log_policy_number= policy_number,
            log_policy_id = policy.id,
            log_policy_issue_date=policy_info.policy_issue_date,
            log_policy_start_date=policy_info.policy_start_date,
            log_policy_expiry_date=policy_info.policy_expiry_date,
            log_insurer_name=policy_info.insurer_name,
            log_insured_mobile=policy_info.insured_mobile,
            log_insured_email=policy_info.insured_email,
            log_insured_address=policy_info.insured_address,
            log_insured_pan=policy_info.insured_pan,
            log_insured_aadhaar=policy_info.insured_aadhaar,
            log_insurance_company=policy_info.insurance_company,
            log_service_provider=policy_info.service_provider,
            log_insurer_contact_name=policy_info.insurer_contact_name,
            log_bqp=policy_info.bqp,
            log_pos_name=policy_info.pos_name,
            log_referral_by=policy_info.referral_by,
            log_branch_name=policy_info.branch_name,
            log_supervisor_name=policy_info.supervisor_name,
            log_policy_type=policy_info.policy_type,
            log_policy_plan=policy_info.policy_plan,
            log_sum_insured=policy_info.sum_insured,
            log_od_premium=policy_info.od_premium,
            log_tp_premium=policy_info.tp_premium,
            log_pa_count=policy_info.pa_count,
            log_pa_amount=policy_info.pa_amount,
            log_driver_count=policy_info.driver_count,
            log_driver_amount=policy_info.driver_amount,
            log_fuel_type=policy_info.fuel_type,
            log_be_fuel_amount=policy_info.be_fuel_amount,
            log_gross_premium=policy_info.gross_premium,
            log_net_premium=policy_info.net_premium,
            log_active= 1,
            action= action
        )
        
        async_task('empPortal.tasks.create_or_update_policyVehicleInfo',index,row,file_id,policy_number,policy)
        
    except Exception as e:
        logger.info(f"Row {index + 2}: PolicyInfo for policy_number: {policy_number}, error : {str(e)}")
        excel_instance.error_rows +=1
        excel_instance.save()    
    
def create_or_update_policyVehicleInfo(index,row,file_id,policy_number,policy):
    try:
        excel_instance = UploadedExcel.objects.get(id=file_id)
        vehicle,created_vehicle = PolicyVehicleInfo.objects.get_or_create(policy_number=policy_number)
        if created_vehicle:
            action = 'Insert'
            logger.info(f"Row {index + 2}: Created new PolicyVehicleInfo for policy_number: {policy_number}")
        else:
            action = 'Update'
            logger.info(f"Row {index + 2}: Updated existing PolicyVehicleInfo for policy_number: {policy_number}")

        update_field(vehicle, 'vehicle_type', row.get('vehicle_type'))
        update_field(vehicle, 'vehicle_make', row.get('vehicle_make'))
        update_field(vehicle, 'vehicle_model', row.get('vehicle_model'))
        update_field(vehicle, 'vehicle_variant', row.get('vehicle_variant'))
        update_field(vehicle, 'fuel_type', row.get('fuel_type'))
        update_field(vehicle, 'gvw', to_int(row.get('gvw')))
        update_field(vehicle, 'cubic_capacity', to_int(row.get('cubic_capacity')))
        update_field(vehicle, 'seating_capacity', to_int(row.get('seating_capacity')))
        update_field(vehicle, 'registration_number', row.get('vehicle_reg_no'))
        update_field(vehicle, 'engine_number', row.get('engine_number'))
        update_field(vehicle, 'chassis_number', row.get('chassis_number'))
        update_field(vehicle, 'manufacture_year', to_int(row.get('manufacture_year')))
        vehicle.save()
        
        logs = PolicyVehicleInfoLog.objects.create(
            policy_vehicle_info_id= vehicle.id,
            log_policy_number= policy_number,
            log_policy_document_id = policy.id,
            log_vehicle_type= vehicle.vehicle_type,
            log_vehicle_make= vehicle.vehicle_make,
            log_vehicle_model= vehicle.vehicle_model,
            log_vehicle_variant= vehicle.vehicle_variant,
            log_fuel_type= vehicle.fuel_type,
            log_gvw= vehicle.gvw,
            log_cubic_capacity= vehicle.cubic_capacity,
            log_seating_capacity= vehicle.seating_capacity,
            log_registration_number= vehicle.registration_number,
            log_engine_number= vehicle.engine_number,
            log_chassis_number= vehicle.chassis_number,
            log_manufacture_year= vehicle.manufacture_year,
            log_active= 1,
            action= action
        )
        
        async_task('empPortal.tasks.create_or_update_agentPaymentDetails',index,row,file_id,policy_number,policy)
        
    except Exception as e:
        logger.info(f"Row {index + 2}: PolicyVehicleInfo for policy_number: {policy_number}, error : {str(e)}")
        excel_instance.error_rows +=1
        excel_instance.save()
                
def create_or_update_agentPaymentDetails(index,row,file_id,policy_number,policy):
    try:
        excel_instance = UploadedExcel.objects.get(id=file_id)
        agent_payment, agent_created = AgentPaymentDetails.objects.get_or_create(policy_number=policy_number)
        if agent_created:
            action = 'Insert'
            logger.info(f"Row {index + 2}: Created new AgentPaymentDetails for policy_number: {policy_number}")
        else:
            action = 'Update'
            logger.info(f"Row {index + 2}: Updated existing AgentPaymentDetails for policy_number: {policy_number}")

        update_field(agent_payment, 'agent_name', row.get('referral_by'))
        update_field(agent_payment, 'agent_payment_mod', row.get('agent_payment_mode'))
        update_field(agent_payment, 'transaction_id', row.get('transaction_id'))
        update_field(agent_payment, 'agent_payment_date', row.get('agent_payment_date'))
        update_field(agent_payment, 'agent_amount', to_int(row.get('agent_amount')))
        update_field(agent_payment, 'agent_remarks', row.get('agent_remark'))
        update_field(agent_payment, 'agent_od_comm', row.get('agent_od_comm_percentage'))
        update_field(agent_payment, 'agent_od_amount', to_int(row.get('agent_od_comm_amount')))
        update_field(agent_payment, 'agent_tp_comm', row.get('agent_comm_tp_percent'))
        update_field(agent_payment, 'agent_tp_amount', to_int(row.get('agent_tp_comm_amount')))
        update_field(agent_payment, 'agent_net_comm', row.get('agent_net_comm_percent'))
        update_field(agent_payment, 'agent_net_amount', to_int(row.get('agent_net_comm_amt')))
        update_field(agent_payment, 'agent_incentive_amount', to_int(row.get('agent_incentive_amt')))
        update_field(agent_payment, 'agent_tds', row.get('agent_tds_percent'))
        update_field(agent_payment, 'agent_tds_amount', to_int(row.get('agent_tds_amt')))
        update_field(agent_payment, 'agent_total_comm_amount', to_int(row.get('agent_total_comm_amt')))
        update_field(agent_payment, 'agent_net_payable_amount', to_int(row.get('agent_net_payable_amt')))
        agent_payment.save()
        
        logs = AgentPaymentDetailsLog.objects.create(
            agent_payment_id= agent_payment.id,
            log_policy_number= policy_number,
            log_policy_document_id = policy.id,
            log_agent_name=agent_payment.agent_name,
            log_agent_payment_mod=agent_payment.agent_payment_mod,
            log_transaction_id=agent_payment.transaction_id,
            log_agent_payment_date=agent_payment.agent_payment_date,
            log_agent_amount=agent_payment.agent_amount,
            log_agent_remarks=agent_payment.agent_remarks,
            log_agent_od_comm=agent_payment.agent_od_comm,
            log_agent_tp_comm=agent_payment.agent_tp_comm,
            log_agent_net_comm=agent_payment.agent_net_comm,
            log_agent_incentive_amount=agent_payment.agent_incentive_amount,
            log_agent_tds=agent_payment.agent_tds,
            log_agent_od_amount=agent_payment.agent_od_amount,
            log_agent_net_amount=agent_payment.agent_net_amount,
            log_agent_tp_amount=agent_payment.agent_tp_amount,
            log_agent_total_comm_amount=agent_payment.agent_total_comm_amount,
            log_agent_net_payable_amount=agent_payment.agent_net_payable_amount,
            log_agent_tds_amount=agent_payment.agent_tds_amount,
            log_active= 1,
            action= action
        )
        async_task('empPortal.tasks.create_or_update_insurerPaymentDetails',index,row,file_id,policy_number,policy)

    except Exception as e:
        logger.info(f"Row {index + 2}: AgentPayment for policy_number: {policy_number}, error : {str(e)}")
        excel_instance.error_rows +=1
        excel_instance.save()
                
def create_or_update_insurerPaymentDetails(index,row,file_id,policy_number,policy):
    try:
        excel_instance = UploadedExcel.objects.get(id=file_id)
        insurer_payment, insurer_payment_created= InsurerPaymentDetails.objects.get_or_create(policy_number=policy_number)
        if insurer_payment_created:
            action="Insert"
            logger.info(f"Row {index + 2}: Created new InsurerPaymentDetails for policy_number: {policy_number}")
        else:
            action="Update"
            logger.info(f"Row {index + 2}: Updated existing InsurerPaymentDetails for policy_number: {policy_number}")

        update_field(insurer_payment, 'insurer_payment_mode', row.get('insurer_payment_mode'))
        update_field(insurer_payment, 'insurer_payment_date', row.get('insurer_payment_date'))
        update_field(insurer_payment, 'insurer_amount', to_int(row.get('insurer_amount')))
        update_field(insurer_payment, 'insurer_remarks', row.get('insurer_remark'))
        update_field(insurer_payment, 'insurer_od_comm', row.get('insurer_od_comm_percent'))
        update_field(insurer_payment, 'insurer_od_amount', to_int(row.get('insurer_agent_od_amt')))
        update_field(insurer_payment, 'insurer_tp_comm', row.get('insurer_tp_percent'))
        update_field(insurer_payment, 'insurer_tp_amount', to_int(row.get('insurer_tp_amt')))
        update_field(insurer_payment, 'insurer_net_comm', row.get('insurer_net_percent'))
        update_field(insurer_payment, 'insurer_net_amount', to_int(row.get('insurer_net_amt')))
        update_field(insurer_payment, 'insurer_tds', row.get('insurer_tds_percent'))
        update_field(insurer_payment, 'insurer_tds_amount', to_int(row.get('insurer_tds_amt')))
        update_field(insurer_payment, 'insurer_incentive_amount', to_int(row.get('insurer_incentive_amt')))
        update_field(insurer_payment, 'insurer_total_comm_amount', to_int(row.get('insurer_total_comm_amt')))
        update_field(insurer_payment, 'insurer_net_payable_amount', to_int(row.get('insurer_net_payable_amt')))
        update_field(insurer_payment, 'insurer_total_commission', to_int(row.get('insurer_total_commision')))
        update_field(insurer_payment, 'insurer_receive_amount', to_int(row.get('insurer_received_amt')))
        update_field(insurer_payment, 'insurer_balance_amount', to_int(row.get('insurer_balance_amount')))
        insurer_payment.save()
        
        logs = InsurerPaymentDetailsLog.objects.create(
            insurer_payment_id= insurer_payment.id,
            log_policy_number= policy_number,
            log_policy_document_id = policy.id,
            log_insurer_payment_mode=insurer_payment.insurer_payment_mode,
            log_insurer_payment_date=insurer_payment.insurer_payment_date,
            log_insurer_amount=insurer_payment.insurer_amount,
            log_insurer_remarks=insurer_payment.insurer_remarks,
            log_insurer_od_comm=insurer_payment.insurer_od_comm,
            log_insurer_net_comm=insurer_payment.insurer_net_comm,
            log_insurer_tp_comm=insurer_payment.insurer_tp_comm,
            log_insurer_incentive_amount=insurer_payment.insurer_incentive_amount,
            log_insurer_tds=insurer_payment.insurer_tds,
            log_insurer_od_amount=insurer_payment.insurer_od_amount,
            log_insurer_net_amount=insurer_payment.insurer_net_amount,
            log_insurer_tp_amount=insurer_payment.insurer_tp_amount,
            log_insurer_total_comm_amount=insurer_payment.insurer_total_comm_amount,
            log_insurer_net_payable_amount=insurer_payment.insurer_net_payable_amount,
            log_insurer_tds_amount=insurer_payment.insurer_tds_amount,
            log_insurer_total_commission=insurer_payment.insurer_total_commission,
            log_insurer_receive_amount=insurer_payment.insurer_receive_amount,
            log_insurer_balance_amount=insurer_payment.insurer_balance_amount,
            log_active= 1,
            action= action
        )
        async_task('empPortal.tasks.create_or_update_franchisePaymentDetails',index,row,file_id,policy_number,policy)

    except Exception as e:
        logger.info(f"Row {index + 2}: InsurerPayment for policy_number: {policy_number}, error : {str(e)}")
        excel_instance.error_rows +=1
        excel_instance.save()

def create_or_update_franchisePaymentDetails(index,row,file_id,policy_number,policy):
    try:
        excel_instance = UploadedExcel.objects.get(id=file_id)
        franchise_payment, franchise_payment_created  = FranchisePayment.objects.get_or_create(policy_number=policy_number)
        if franchise_payment_created:
            action = 'Insert'
            logger.info(f"Row {index + 2}: Created new FranchisePayment for policy_number: {policy_number}")
        else:
            action = 'Update'
            logger.info(f"Row {index + 2}: Updated existing FranchisePayment for policy_number: {policy_number}")
        
        update_field(franchise_payment, 'franchise_od_comm', row.get('franchise_od_comm_percent'))
        update_field(franchise_payment, 'franchise_od_amount', to_int(row.get('franchise_od_comm_amt')))
        update_field(franchise_payment, 'franchise_net_comm', row.get('franchise_net_comm_percent'))
        update_field(franchise_payment, 'franchise_net_amount', to_int(row.get('franchise_net_comm_amt')))
        update_field(franchise_payment, 'franchise_tp_comm', row.get('franchise_tp_comm_percent'))
        update_field(franchise_payment, 'franchise_tp_amount', to_int(row.get('franchise_tp_comm_amt')))
        update_field(franchise_payment, 'franchise_incentive_amount', to_int(row.get('franchise_incentive_amt')))
        update_field(franchise_payment, 'franchise_tds', row.get('franchise_tds_percent'))
        update_field(franchise_payment, 'franchise_tds_amount', to_int(row.get('franchise_tds_amt')))
        update_field(franchise_payment, 'franchise_total_comm_amount', to_int(row.get('franchise_total_comm_amt')))
        update_field(franchise_payment, 'franchise_net_payable_amount', to_int(row.get('franchise_net_payable_amt')))
        franchise_payment.save()
        
        logs = FranchisePaymentLog.objects.create(
            franchise_payment_id= franchise_payment.id,
            log_policy_document_id= policy.id,
            log_policy_number= policy_number,
            log_franchise_od_comm= franchise_payment.franchise_od_comm,
            log_franchise_net_comm= franchise_payment.franchise_net_comm,
            log_franchise_tp_comm= franchise_payment.franchise_tp_comm,
            log_franchise_incentive_amount= franchise_payment.franchise_incentive_amount,
            log_franchise_tds= franchise_payment.franchise_tds,
            log_franchise_od_amount= franchise_payment.franchise_od_amount,
            log_franchise_net_amount= franchise_payment.franchise_net_amount,
            log_franchise_tp_amount= franchise_payment.franchise_tp_amount,
            log_franchise_total_comm_amount= franchise_payment.franchise_total_comm_amount,
            log_franchise_net_payable_amount= franchise_payment.franchise_net_payable_amount,
            log_franchise_tds_amount= franchise_payment.franchise_tds_amount,
            log_active= 1,
            action= action
        )
        
        excel_instance.success_rows +=1
        excel_instance.save()
    except Exception as e:
        logger.info(f"Row {index + 2}: FranchisePayment for policy_number: {policy_number}, error : {str(e)}")
        excel_instance.error_rows +=1
        excel_instance.save()