# from sre_parse import State
from empPortal.model.StateCity import State,City
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from datetime import datetime
from django.utils.timezone import now
from django.utils.timezone import localtime
from empPortal.model import Referral, Partner, InsuranceType, InsuranceCategory, InsuranceProduct
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from empPortal.model.customer import Customer

class Roles(models.Model):
    roleGenID = models.CharField(max_length=255)
    roleName = models.CharField(max_length=255)
    roleDepartment = models.CharField(max_length=255)
    primaryRoleId = models.CharField(max_length=255)
    roleDescription = models.CharField(max_length=255)

    class Meta:
        db_table = 'roles'

from django.db import models
## Source master -----> source ##
class SourceMaster(models.Model):
    source_name       = models.CharField(max_length=255)
    sort_source_name  = models.CharField(max_length=255)
    status            = models.BooleanField(default=True)  # True=1, False=0
    created_at        = models.DateTimeField(auto_now_add=True)
    updated_at        = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'source_master'

## BQPMASTER Details ##
class BqpMaster(models.Model):
    bqp_fname =models.CharField(max_length=100)
    bqp_lname =models.CharField(max_length=100)
    pan_number =models.CharField(max_length=10,unique=True)
    mobile_number = models.CharField(max_length=15, null=True, blank=True)
    email_address =models.CharField(max_length=255,null=True, blank=True)
    bqp_status = models.BooleanField(default=True)
    created_at =models.DateTimeField(auto_now_add=True)
    updated_at =models.DateTimeField(auto_now=True)

    class Meta:
        db_table ="bqp_master"

    @property
    def bqp_name(self):
        return self.bqp_fname +" "+ self.bqp_lname
        
class Branch(models.Model):
    franchise_id = models.IntegerField(null=True, blank=True, verbose_name="Franchise ID")
    branch_name = models.CharField(max_length=255, null=True, blank=True, verbose_name="Branch Name")
    contact_person = models.CharField(max_length=255, null=True, blank=True, verbose_name="Contact Person")
    mobile = models.CharField(max_length=15, null=True, blank=True, verbose_name="Mobile")
    email = models.EmailField(max_length=255, null=True, blank=True, verbose_name="Email")

    address = models.TextField(null=True, blank=True, verbose_name="Address")
    city = models.CharField(max_length=100, null=True, blank=True, verbose_name="City")
    state = models.CharField(max_length=100, null=True, blank=True, verbose_name="State")
    pincode = models.CharField(max_length=10, null=True, blank=True, verbose_name="Pincode")

    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Inactive', 'Inactive'),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, null=True, blank=True, default='Active', verbose_name="Status")

    created_at = models.DateTimeField(default=timezone.now, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        db_table = 'branches'
        verbose_name = "Branch"
        verbose_name_plural = "Branches"

    def __str__(self):
        return f"{self.branch_name if self.branch_name else 'Unnamed Branch'}"

    def status_type(self):
        return "Active" if self.status == "Active" else "Inactive"


class Commission(models.Model):
    rm_name  =models.CharField(max_length=255, unique=True)
    member_id = models.CharField(max_length=20, null=True, blank=True)
    product_id = models.CharField(max_length=20, null=True, blank=True)
    sub_broker_id = models.CharField(max_length=20, null=True, blank=True)
    tp_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    od_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    net_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    created_by = models.CharField(max_length=10, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)

    class Meta:
        db_table = "commissions"

    def __str__(self):
        return f"Commission {self.id} - Insurer {self.member_id}"
    
    from django.db import models

class VehicleInfo(models.Model):
    customer_id = models.CharField(max_length=20, null=True, blank=True)  # Nullable as per SQL table
    registration_number = models.CharField(max_length=20, null=True, blank=True)
    registration_date = models.DateField(null=True, blank=True)  # Added registration_date
    vehicle_type = models.CharField(max_length=50, null=True, blank=True)
    make = models.CharField(max_length=50, null=True, blank=True)
    model = models.CharField(max_length=50, null=True, blank=True)
    variant = models.CharField(max_length=50, null=True, blank=True)
    year_of_manufacture = models.IntegerField(null=True, blank=True)
    registration_state = models.CharField(max_length=50, null=True, blank=True)
    registration_city = models.CharField(max_length=50, null=True, blank=True)
    chassis_number = models.CharField(max_length=50, null=True, blank=True)
    engine_number = models.CharField(max_length=50, null=True, blank=True)
    claim_history = models.CharField(max_length=10, choices=[("Yes", "Yes"), ("No", "No")], null=True, blank=True)
    ncb = models.CharField(max_length=10, choices=[("Yes", "Yes"), ("No", "No")], default="No", null=True, blank=True)
    ncb_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    idv_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    policy_type = models.CharField(max_length=50, null=True, blank=True)
    policy_duration = models.CharField(max_length=50, null=True, blank=True)
    policy_companies = models.CharField(max_length=50, null=True, blank=True)
    addons = models.CharField(max_length=50, null=True, blank=True)

    # Additional fields from your request
    owner_name = models.CharField(max_length=255, null=True, blank=True)
    father_name = models.CharField(max_length=255, null=True, blank=True)
    state_code = models.CharField(max_length=20, null=True, blank=True)
    location = models.CharField(max_length=255, null=True, blank=True)
    vehicle_category = models.CharField(max_length=100, null=True, blank=True)
    vehicle_class_description = models.CharField(max_length=100, null=True, blank=True)
    body_type_description = models.CharField(max_length=100, null=True, blank=True)
    vehicle_color = models.CharField(max_length=50, null=True, blank=True)
    vehicle_cubic_capacity = models.CharField(max_length=20, null=True, blank=True)
    vehicle_gross_weight = models.CharField(max_length=20, null=True, blank=True)
    vehicle_seating_capacity = models.CharField(max_length=20, null=True, blank=True)
    vehicle_fuel_description = models.CharField(max_length=50, null=True, blank=True)
    vehicle_owner_number = models.CharField(max_length=20, null=True, blank=True)
    rc_expiry_date = models.DateField(null=True, blank=True)
    rc_pucc_expiry_date = models.DateField(null=True, blank=True)
    insurance_company = models.CharField(max_length=255, null=True, blank=True)
    insurance_expiry_date = models.DateField(null=True, blank=True)
    insurance_policy_number = models.CharField(max_length=255, null=True, blank=True)

    active = models.BooleanField(default=True)  # 1 for active, 0 for inactive
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "quotation_vehicle_info"

    def __str__(self):
        return f"VehicleInfo {self.registration_number} - {self.customer_id}"



class QuotationCustomer(models.Model):
    customer_id = models.CharField(max_length=20, unique=True)  # For values like CUS2343545
    mobile_number = models.CharField(max_length=15, null=True, blank=True)
    email_address = models.CharField(max_length=255, null=True, blank=True)
    quote_date = models.DateField(null=True, blank=True)
    name_as_per_pan = models.CharField(max_length=255, null=True, blank=True)
    pan_card_number = models.CharField(max_length=10, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    state = models.CharField(max_length=100, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    pincode = models.CharField(max_length=10, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    active = models.BooleanField(default=True)  # 1 for active, 0 for inactive
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # vehicleinfo = models.ForeignKey(VehicleInfo, on_delete=models.CASCADE)
    class Meta:
        db_table = "quotation_customers"

    def __str__(self):
        return f"QuotationCustomer {self.customer_id} - {self.name_as_per_pan}"
    
class Leads(models.Model):
    partner = models.ForeignKey(Partner, on_delete=models.SET_NULL,null=True, related_name='lead_by_partner')  
    lead_id = models.CharField(max_length=20, unique=True)  # Unique customer identifier (e.g., CUS2343545)
    mobile_number = models.CharField(max_length=15)  # Customer's mobile number
    email_address = models.CharField(max_length=255)  # Customer's email address
    quote_date = models.CharField(max_length=25,null=True, blank=True)  # Quote date
    name_as_per_pan = models.CharField(max_length=255)  # Customer's name as per PAN
    pan_card_number = models.CharField(max_length=20, null=True, blank=True)  # PAN card number (optional)
    date_of_birth = models.CharField(max_length=25,null=True, blank=True)  # Customer's date of birth (optional)
    state = models.ForeignKey(State, on_delete=models.SET_NULL, null=True, blank=True)
    city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True, blank=True)
    pincode = models.CharField(max_length=10, null=True, blank=True)  # Pincode of the customer
    address = models.TextField(null=True, blank=True)  # Address of the customer
    lead_description = models.TextField(null=True, blank=True)
    lead_source = models.CharField(max_length=25, null=True, blank=True)  
    referral_by = models.CharField(max_length=25, null=True, blank=True)  
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True, related_name='leads_assigned')  
    assigned_manager = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True, related_name='leads_assigned_manager')  
    assigned_teamleader = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True, related_name='leads_assigned_teamleader')  
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True)  
    lead_status_type = models.IntegerField( null=True, blank=True)  
    lead_tag = models.IntegerField( null=True, blank=True)  
    referral_mobile_no = models.BigIntegerField(null=True, blank=True)
    referral_name = models.CharField(max_length=255,null=True,blank=True)
    lead_source_medium = models.IntegerField(null=True, blank=True)
    policy_date = models.DateField(null=True, blank=True)
    sales_manager = models.CharField(max_length=100, null=True, blank=True)
    agent_name = models.CharField(max_length=100, null=True, blank=True)
    insurance_company = models.CharField(max_length=200, null=True, blank=True)
    policy_type = models.CharField(max_length=100, null=True, blank=True)
    policy_number = models.CharField(max_length=100, null=True, blank=True)
    vehicle_type = models.CharField(max_length=100, null=True, blank=True)
    make_and_model = models.CharField(max_length=200, null=True, blank=True)
    fuel_type = models.CharField(max_length=100, null=True, blank=True)
    registration_number = models.CharField(max_length=100, null=True, blank=True)
    manufacturing_year = models.IntegerField(null=True, blank=True)
    sum_insured = models.BigIntegerField(null=True, blank=True)
    ncb = models.IntegerField(null=True, blank=True)
    od_premium = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    tp_premium = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    net_premium = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    gross_premium = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    risk_start_date = models.DateField(null=True, blank=True)
    lead_insurance_type = models.ForeignKey(InsuranceType,on_delete=models.SET_NULL,null=True,blank=True)
    lead_insurance_category = models.ForeignKey(InsuranceCategory, on_delete=models.SET_NULL, null=True, blank=True)
    lead_insurance_product = models.ForeignKey(InsuranceProduct, on_delete=models.SET_NULL, null=True, blank=True)
    lead_first_name = models.CharField(max_length=255,null=True,blank=True)
    lead_last_name = models.CharField(max_length=255,null=True,blank=True)
    lead_customer_identity_no = models.CharField(max_length=255,null=True,blank=True)
    lead_customer_gender = models.IntegerField(null=True,blank=True)
    previous_idv_amount = models.IntegerField(null=True,blank=True)
    previous_sum_insured = models.IntegerField(null=True,blank=True)
    claim_amount = models.IntegerField(null=True,blank=True)
    mgf_year = models.IntegerField(null=True,blank=True)
    claim_made = models.IntegerField(null=True,blank=True)
    previous_insurer_name = models.CharField(max_length=255,null=True,blank=True)
    previous_policy_source = models.CharField(max_length=255,null=True,blank=True)
    expiry_status = models.CharField(max_length=255,null=True,blank=True)
    vehicle_class = models.CharField(max_length=255,null=True,blank=True)
    insurance_type = models.CharField(max_length=255,null=True,blank=True)
    vehicle_reg_no = models.CharField(max_length=255,null=True,blank=True)
    product_category = models.CharField(max_length=255,null=True,blank=True)
    vehicle_model = models.CharField(max_length=255,null=True,blank=True)
    vehicle_make = models.CharField(max_length=255,null=True,blank=True)
    policy_end_date = models.DateField(null=True, blank=True)
    policy_date = models.DateField(null=True, blank=True)
    sales_manager = models.CharField(max_length=100, null=True, blank=True)
    agent_name = models.CharField(max_length=100, null=True, blank=True)
    insurance_company = models.CharField(max_length=200, null=True, blank=True)
    policy_type = models.CharField(max_length=100, null=True, blank=True)
    policy_number = models.CharField(max_length=100, null=True, blank=True)
    vehicle_type = models.CharField(max_length=100, null=True, blank=True)
    make_and_model = models.CharField(max_length=200, null=True, blank=True)
    fuel_type = models.CharField(max_length=100, null=True, blank=True)
    registration_number = models.CharField(max_length=100, null=True, blank=True)
    manufacturing_year = models.IntegerField(null=True, blank=True)
    sum_insured = models.BigIntegerField(null=True, blank=True)
    ncb = models.IntegerField(null=True, blank=True)
    od_premium = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    tp_premium = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    net_premium = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    gross_premium = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    risk_start_date = models.CharField(max_length=255)
    lead_source_type = models.ForeignKey(SourceMaster,on_delete=models.SET_NULL,null=True,blank=True)

    created_at = models.DateTimeField(auto_now_add=True) 
    
    updated_at = models.DateTimeField(auto_now=True)  
    lead_customer = models.ForeignKey(Customer,on_delete=models.SET_NULL,null=True,blank=True,related_name='fk_lead_customer_id')
    
    status = models.BooleanField(default=True)
    posp = models.ForeignKey( settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='posp_user_id'
    )
    lead_type = models.CharField(
        max_length=10, 
        choices=[('MOTOR', 'MOTOR'), ('HEALTH', 'HEALTH'), ('TERM', 'TERM')], 
        default='MOTOR'
    )
    created_by =  created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='leads_created'
    )
    parent_lead = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='child_lead'
    )
    class Meta:
        db_table = 'leads'  

    def __str__(self):
        return f"Lead - {self.name_as_per_pan}"

class QuotationVehicleDetail(models.Model):
    registration_number = models.CharField(max_length=20, null=True, blank=True)
    vehicle_details = models.TextField(null=True, blank=True)
    active = models.BooleanField(default=True)  # Default to active (1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "quotation_vehicle_details"

    def __str__(self):
        return f"Vehicle {self.registration_number or 'N/A'}"

from django.db import models
from django.utils.timezone import now

class PolicyDocument(models.Model):
    
    OPERATOR_STATUS_CHOICES = [
        ('0', 'Pending'),
        ('1', 'Approved'),
        ('2', 'Rejected'),
    ]

    QUALITY_STATUS_CHOICES = [
        ('0', 'Pending'),
        ('1', 'Approved'),
        ('2', 'Rejected'),
    ]

    filename = models.CharField(max_length=255)
    insurance_provider = models.CharField(max_length=255)
    policy_number = models.CharField(max_length=255)
    policy_issue_date = models.CharField(max_length=255)
    policy_expiry_date = models.CharField(max_length=255)
    vehicle_number = models.CharField(max_length=255)
    holder_name = models.CharField(max_length=255)
    
    operator_verification_status = models.CharField(
        max_length=1,
        choices=OPERATOR_STATUS_CHOICES,
        default='0'
    )
    operator_remark = models.TextField(blank=True, null=True)
    operator_policy_verification_by = models.CharField(max_length=20, null=True, blank=True)  # Added column

    quality_check_status = models.CharField(
        max_length=1,
        choices=QUALITY_STATUS_CHOICES,
        default='0'
    )
    quality_remark = models.TextField(blank=True, null=True)
    quality_policy_check_by = models.CharField(max_length=20, null=True, blank=True)  # Added column
    
    policy_period = models.CharField(max_length=255)
    filepath = models.CharField(max_length=255)
    policy_premium = models.CharField(max_length=255)
    policy_total_premium = models.CharField(max_length=255)
    sum_insured = models.CharField(max_length=255)
    rm_name = models.CharField(max_length=255)
    rm_id = models.IntegerField()
    insurance_company_id = models.IntegerField(null=True)
    extracted_text = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.IntegerField()
    coverage_details = models.JSONField()
    policy_start_date = models.CharField(max_length=255)
    payment_status = models.CharField(max_length=255)
    policy_type = models.CharField(max_length=255)
    vehicle_type = models.CharField(max_length=255)
    vehicle_make = models.CharField(max_length=255)
    vehicle_model = models.CharField(max_length=255)
    vehicle_gross_weight = models.CharField(max_length=255)
    vehicle_manuf_date = models.CharField(max_length=255)
    gst = models.CharField(max_length=255)
    od_premium = models.CharField(max_length=255)
    tp_premium = models.CharField(max_length=255)
    bulk_log_id = models.IntegerField()
    od_percent = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    tp_percent = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    net_percent = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    insurer_tp_commission = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    insurer_od_commission = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    insurer_net_commission = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    ACTIVE_CHOICES = (
        ('1', 'Active'),
        ('0', 'Inactive'),
    )

    def __str__(self):
        return self.filename    
    
    # commission = models.ForeignKey(Commission, to_field="rm_name", on_delete=models.SET_NULL, null=True, blank=True)

    def commission(self):
         return Commission.objects.filter(member_id=self.rm_id ).first()

    @property
    def start_date(self):
        try:
            return datetime.strptime(self.policy_start_date, "%Y-%m-%d %H:%M:%S").strftime("%d-%m-%Y")
        except (ValueError, TypeError):
            return None

    @property
    def issue_date(self):
        try:
            return datetime.strptime(self.policy_issue_date, "%Y-%m-%d %H:%M:%S").strftime("%d-%m-%Y")
        except (ValueError, TypeError):
            return None

    @property
    def expiry_date(self):
        try:
            return datetime.strptime(self.policy_expiry_date, "%Y-%m-%d %H:%M:%S").strftime("%d-%m-%Y")
        except (ValueError, TypeError):
            return None
        
    @property
    def agent_payment_details(self):
        from .models import AgentPaymentDetails  # Lazy import inside the method to avoid circular import
        try:
            return AgentPaymentDetails.objects.get(policy_id=self.id)
        except AgentPaymentDetails.DoesNotExist:
            return None
        
    @property
    def insurer_payment_details(self):
        from .models import InsurerPaymentDetails 
        try:
            return InsurerPaymentDetails.objects.get(policy_id=self.id)
        except InsurerPaymentDetails.DoesNotExist:
            return None 
        
    @property
    def insurerInfo(self):
        from empPortal.model import Insurance  
        try:
            return Insurance.objects.get(id=self.insurance_company_id)
        except Insurance.DoesNotExist:
            return None

    @property
    def franchise_payment_details(self):
        from .models import FranchisePayment  # Lazy import inside the method to avoid circular import
        try:
            return FranchisePayment.objects.get(policy_id=self.id)
        except FranchisePayment.DoesNotExist:
            return None

    class Meta:
        db_table = 'policydocument'


from django.db import models

class PolicyInfo(models.Model):
    policy = models.ForeignKey(PolicyDocument, on_delete=models.CASCADE, related_name='policy_info')
    # policy_id = models.CharField(max_length=20, null=True, blank=True)

    # Basic Policy
    policy_number = models.CharField(max_length=100, null=True, blank=True)
    policy_issue_date = models.CharField(max_length=35, null=True, blank=True)
    policy_start_date = models.CharField(max_length=35, null=True, blank=True)
    policy_expiry_date = models.CharField(max_length=35, null=True, blank=True)

    # Insured Details
    insurer_name = models.CharField(max_length=255, null=True, blank=True)
    insured_name = models.CharField(max_length=255, null=True, blank=True)
    insured_mobile = models.CharField(max_length=15, null=True, blank=True)
    insured_email = models.CharField(max_length=255, null=True, blank=True)
    insured_address = models.TextField(null=True, blank=True)
    insured_pan = models.CharField(max_length=20, null=True, blank=True)
    insured_aadhaar = models.CharField(max_length=20, null=True, blank=True)

    # Policy Details
    insurance_company = models.CharField(max_length=255, null=True, blank=True)
    service_provider = models.CharField(max_length=255, null=True, blank=True)
    insurer_contact_name = models.CharField(max_length=255, null=True, blank=True)
    # bqp = models.CharField(max_length=255, null=True, blank=True)
    bqp = models.ForeignKey(BqpMaster,on_delete=models.SET_NULL,null=True,blank=True)
    pos_name = models.CharField(max_length=255, null=True, blank=True)
    referral_by = models.CharField(max_length=50, null=True, blank=True)
    
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True)
    branch_name = models.CharField(max_length=255, null=True, blank=True)
    supervisor_name = models.CharField(max_length=255, null=True, blank=True)
    policy_type = models.CharField(max_length=255, null=True, blank=True)
    policy_plan = models.CharField(max_length=255, null=True, blank=True)

    sum_insured = models.CharField(max_length=20, null=True, blank=True)
    od_premium = models.CharField(max_length=20, null=True, blank=True)
    tp_premium = models.CharField(max_length=20, null=True, blank=True)
    pa_count = models.CharField(max_length=20, default='0', null=True, blank=True)
    pa_amount = models.CharField(max_length=20, null=True, blank=True)
    driver_count = models.CharField(max_length=20, null=True, blank=True)
    driver_amount = models.CharField(max_length=20, null=True, blank=True)
    fuel_type = models.CharField(max_length=50, null=True, blank=True)
    be_fuel_amount = models.CharField(max_length=50, null=True, blank=True)
    gross_premium = models.CharField(max_length=50, null=True, blank=True)
    net_premium = models.CharField(max_length=50, null=True, blank=True)
    gst_premium = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, null=True, blank=True)
    active = models.CharField(max_length=1, choices=[('0', 'Inactive'), ('1', 'Active')], default='1')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "policy_info"

    def __str__(self):
        return f"Policy {self.policy_number} - {self.policy_id}"
    
    @property
    def policy_month_year(self):
        if not self.policy_issue_date:
            return None
        try:
            issue_date = datetime.strptime(self.policy_issue_date.strip(), "%Y-%m-%d %H:%M:%S")
            return issue_date.strftime("%b-%Y")  # e.g., May-2023
        except ValueError:
            return None
        
    @property
    def issue_date(self):
        try:
            return datetime.strptime(self.policy_issue_date, "%Y-%m-%d %H:%M:%S").strftime("%d-%m-%Y")
        except (ValueError, TypeError):
            return None
        
    @property
    def start_date(self):
        try:
            return datetime.strptime(self.policy_start_date, "%Y-%m-%d %H:%M:%S").strftime("%d-%m-%Y")
        except (ValueError, TypeError):
            return None
        
    @property
    def end_date(self):
        try:
            return datetime.strptime(self.policy_expiry_date, "%Y-%m-%d %H:%M:%S").strftime("%d-%m-%Y")
        except (ValueError, TypeError):
            return None
        
    @property
    def policy_tenure(self):
        try:
            start = datetime.strptime(self.policy_start_date, "%Y-%m-%d %H:%M:%S")
            end = datetime.strptime(self.policy_expiry_date, "%Y-%m-%d %H:%M:%S")
            return int((end.year - start.year) + ((end.month - start.month) / 12))
        except (ValueError,TypeError):
            return None
        
    @property
    def payment_date(self):
        try:
           return datetime.strptime(self.policy_issue_date, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d")
        except (ValueError,TypeError):
            return None

class AgentPaymentDetails(models.Model):
    policy = models.ForeignKey(PolicyDocument, on_delete=models.CASCADE, related_name='policy_agent_info')
    referral = models.ForeignKey(Referral, on_delete=models.CASCADE, related_name='policy_referal')
    policy_number = models.CharField(max_length=255)
    agent_name = models.CharField(max_length=255)
    agent_payment_mod = models.CharField(max_length=255)
    transaction_id = models.CharField(max_length=255)
    agent_payment_date = models.CharField(max_length=255)
    agent_amount = models.CharField(max_length=255)
    agent_remarks = models.CharField(max_length=255)
    agent_od_comm = models.CharField(max_length=255)
    agent_tp_comm = models.CharField(max_length=255)
    agent_net_comm = models.CharField(max_length=255)
    agent_incentive_amount = models.CharField(max_length=255)
    agent_tds = models.CharField(max_length=255)
    agent_od_amount = models.CharField(max_length=255)
    agent_net_amount = models.CharField(max_length=255)
    agent_tp_amount = models.CharField(max_length=255)
    agent_total_comm_amount = models.CharField(max_length=255)
    agent_net_payable_amount = models.CharField(max_length=255)
    agent_tds_amount = models.CharField(max_length=255)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='agent_info_updated_by'
    )
    active = models.CharField(max_length=1, choices=[('0', 'Inactive'), ('1', 'Active')], default='1')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'agent_payment_details'

    @property
    def payment_date(self):
        try:
            return datetime.strptime(self.agent_payment_date, "%Y-%m-%d").strftime("%d-%m-%Y")
        except(ValueError, TypeError):
            return None 
    def __str__(self):
        return f"{self.agent_name} - {self.policy_number}"
    
class FranchisePayment(models.Model):
    policy = models.ForeignKey(PolicyDocument, on_delete=models.CASCADE, related_name='policy_franchise_info')
    policy_number = models.CharField(max_length=50, unique=True)
    franchise_od_comm = models.CharField(max_length=50, blank=True, null=True)
    franchise_net_comm = models.CharField(max_length=50, blank=True, null=True)
    franchise_tp_comm = models.CharField(max_length=50, blank=True, null=True)
    franchise_incentive_amount = models.CharField(max_length=50, blank=True, null=True)
    franchise_tds = models.CharField(max_length=50, blank=True, null=True)
    franchise_od_amount = models.CharField(max_length=50, blank=True, null=True)
    franchise_net_amount = models.CharField(max_length=50, blank=True, null=True)
    franchise_tp_amount = models.CharField(max_length=50, blank=True, null=True)
    franchise_total_comm_amount = models.CharField(max_length=50, blank=True, null=True)
    franchise_net_payable_amount = models.CharField(max_length=50, blank=True, null=True)
    franchise_tds_amount = models.CharField(max_length=50, blank=True, null=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='franchise_payments_updated_by'
    )
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'franchise_payments'
        verbose_name = 'Franchise Payment'
        verbose_name_plural = 'Franchise Payments'

    def __str__(self):
        return f"Franchise Payment #{self.id}"

class PolicyUploadDoc(models.Model):
    policy = models.ForeignKey(PolicyDocument, on_delete=models.CASCADE, related_name='policy_upload_doc_info')
    policy_number = models.CharField(max_length=100)
    re_other_endorsement = models.FileField(upload_to='policy_doc/', null=True, blank=True)
    previous_policy = models.FileField(upload_to='policy_doc/', null=True, blank=True)
    kyc_document = models.FileField(upload_to='policy_doc/', null=True, blank=True)
    proposal_document = models.FileField(upload_to='policy_doc/', null=True, blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'policy_upload_docs'  # 👈 This sets the exact table name

    def __str__(self):
        return f"Documents for Policy: {self.policy_number}"

class InsurerPaymentDetails(models.Model):
    policy = models.ForeignKey(PolicyDocument, on_delete=models.CASCADE, related_name='policy_insurer_info')
    policy_number = models.CharField(max_length=100, unique=True)

    insurer_payment_mode = models.CharField(max_length=100, blank=True, null=True)
    insurer_payment_date = models.CharField(max_length=100, blank=True, null=True)
    insurer_amount = models.CharField(max_length=50, blank=True, null=True)
    insurer_remarks = models.TextField(blank=True, null=True)

    insurer_od_comm = models.CharField(max_length=50, blank=True, null=True)
    insurer_net_comm = models.CharField(max_length=50, blank=True, null=True)
    insurer_tp_comm = models.CharField(max_length=50, blank=True, null=True)
    insurer_incentive_amount = models.CharField(max_length=50, blank=True, null=True)
    insurer_tds = models.CharField(max_length=50, blank=True, null=True)

    insurer_od_amount = models.CharField(max_length=50, blank=True, null=True)
    insurer_net_amount = models.CharField(max_length=50, blank=True, null=True)
    insurer_tp_amount = models.CharField(max_length=50, blank=True, null=True)
    insurer_total_comm_amount = models.CharField(max_length=50, blank=True, null=True)
    insurer_net_payable_amount = models.CharField(max_length=50, blank=True, null=True)
    insurer_tds_amount = models.CharField(max_length=50, blank=True, null=True)
    
    insurer_total_commission = models.CharField(max_length=50, blank=True, null=True)
    insurer_receive_amount = models.CharField(max_length=50, blank=True, null=True)
    insurer_balance_amount = models.CharField(max_length=50, blank=True, null=True)
    
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='insurer_payment_details_updated_by'
    )

    active = models.CharField(max_length=1, choices=[('0', 'Inactive'), ('1', 'Active')], default='1')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'insurer_payment_details'

    def __str__(self):
        return f"Insurer Payment for {self.policy_number}"
    
class PolicyVehicleInfo(models.Model):
    policy = models.ForeignKey(PolicyDocument, on_delete=models.CASCADE, related_name='policy_vehicle_info')
    policy_number = models.CharField(max_length=100)
    vehicle_type = models.CharField(max_length=100, null=True, blank=True)
    vehicle_make = models.CharField(max_length=100, null=True, blank=True)
    vehicle_model = models.CharField(max_length=100, null=True, blank=True)
    vehicle_variant = models.CharField(max_length=100, null=True, blank=True)
    fuel_type = models.CharField(max_length=30, null=True, blank=True)  # Originally ENUM('Petrol', 'Diesel')

    gvw = models.CharField(max_length=50, null=True, blank=True)
    cubic_capacity = models.CharField(max_length=50, null=True, blank=True)
    seating_capacity = models.CharField(max_length=10, null=True, blank=True)
    ncb = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    registration_number = models.CharField(max_length=100, null=True, blank=True)
    engine_number = models.CharField(max_length=100, null=True, blank=True)
    chassis_number = models.CharField(max_length=100, null=True, blank=True)
    manufacture_year = models.CharField(max_length=4, null=True, blank=True)

    active = models.CharField(max_length=1, choices=[('0', 'Inactive'), ('1', 'Active')], default='1')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "policy_vehicle_info"

    def __str__(self):
        return f"Vehicle Info - {self.policy_number}"

class CommissionHistory(models.Model):
    id = models.BigAutoField(primary_key=True)
    member_id = models.CharField(max_length=20, null=True, blank=True)
    commission_id = models.BigIntegerField(null=True, blank=True)
    insurer_id = models.BigIntegerField(null=True, blank=True)
    rm_name = models.CharField(max_length=220, null=True, blank=True)
    product_id = models.CharField(max_length=10, null=True, blank=True)
    sub_broker_id = models.CharField(max_length=20, null=True, blank=True)
    tp_percentage = models.CharField(max_length=10, null=True, blank=True)
    od_percentage = models.CharField(max_length=10, null=True, blank=True)
    net_percentage = models.CharField(max_length=10, null=True, blank=True)
    created_by = models.CharField(max_length=10, null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=now)
    active = models.BooleanField(default=True)
    
    class Meta:
        db_table = "commissions_logs"

    def __str__(self):
        return f"Commission {self.id} - {self.od_percentage}% / {self.net_percentage}%"
        
 
class UsersManager(BaseUserManager):
    def create_user(self,email,phone=None,password=None,**extra_fields):
        # create and return a user with a email phone and password
        if not email:
            raise ValueError("The email field must be set")
        
        email = self.normalize_email(email)
        user = self.model(email=email,phone=phone,**extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
        
    def create_super_user(self,email,phone=None,password=None,*extra_fields):
        # Creates and returns a superuser with an email, phone, and password.
        extra_fields.setdefault('is_staff',True)
        extra_fields.setdefault('is_superuser',True)
        return self.create_user(email,phone,password,**extra_fields)
    
class Users(AbstractBaseUser):
    user_gen_id = models.CharField(max_length=255)
    user_name = models.CharField(max_length=255)
    first_name = models.CharField(max_length=255)
    activation_status = models.CharField(max_length=10)
    last_name = models.CharField(max_length=255)
    email = models.CharField(max_length=255, unique=True)
    email_otp = models.CharField(max_length=10, null=True, blank=True)
    profile_image = models.FileField(upload_to='uploads/profile_images/', null=True, blank=True)  # Change to FileField
    email_verified = models.BooleanField(default=False)
    phone = models.BigIntegerField(null=True, blank=True)
    phone_otp = models.CharField(max_length=10, null=True, blank=True)
    phone_verified = models.BooleanField(default=False)
    gender = models.PositiveSmallIntegerField(null=True, blank=True) 
    pan_no = models.CharField(max_length=20, null=True, blank=True)
    exam_eligibility = models.PositiveSmallIntegerField(null=True, blank=True, default=0) 
    exam_attempt = models.PositiveSmallIntegerField(null=True, blank=True, default=0) 
    exam_pass = models.PositiveSmallIntegerField(null=True, blank=True, default=0) 
    branch_head = models.PositiveSmallIntegerField(null=True, blank=True, default=0) 
    exam_last_attempted_on = models.DateTimeField(null=True)
    dob = models.CharField(max_length=255)
    state = models.CharField(max_length=255)
    city = models.CharField(max_length=255)
    pincode = models.CharField(max_length=255)
    address = models.CharField(max_length=400)

    role = models.ForeignKey(Roles, on_delete=models.CASCADE, null=True)
    role_name = models.CharField(max_length=255)
    branch_id = models.CharField(max_length=20, null=True, blank=True)
    department_id = models.CharField(max_length=20, null=True, blank=True)
    senior_id = models.CharField(max_length=20, null=True, blank=True)
    status = models.IntegerField(default=1)
    activation_status_updated_at = models.DateTimeField(null=True, blank=True)
    user_active_updated_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    password = models.CharField(max_length=255, null=True)
    annual_ctc = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)
    monthly_ctc = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)
    target_percent = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)
    target_amt = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)
    monthly_target_amt = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)
    ## bqp id ##
    bqp = models.ForeignKey(BqpMaster, on_delete=models.SET_NULL, null=True, blank=True)


    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    user_active = models.BooleanField(default=True)
    is_login_available = models.BooleanField(default=False)
    is_reset_pass_available = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    
    
    objects = UsersManager()
    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = ['user_name']
    class Meta:
        db_table = 'users'

    @property
    def roleName(self):
        try:
            return Roles.objects.get(id=self.role_id)
        except Roles.DoesNotExist:
            return None
    
    @property
    def department(self):
        try:
            return Department.objects.get(id=self.department_id)
        except Department.DoesNotExist:
            return None
        
    @property
    def branch(self):
        try:
            return Branch.objects.get(id=self.branch_id)
        except Branch.DoesNotExist:
            return None
        
    def bqpData(self):
        try:
            return BqpMaster.objects.get(id=self.bqp_id)
        except BqpMaster.DoesNotExist:
            return None    
        
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
    
    def role_names(self):
        if self.role:
            return self.role.roleName
        return self.role_name

    def status_type(self):
        if self.status == 1:
            return 'Active'
        elif self.status == 2:
            return 'Inactive'
        else :
            return 'N/A'
        
    @property
    def partner(self):
        from empPortal.model import Partner  # Lazy import inside the method to avoid circular import
        try:
            return Partner.objects.get(user_id=self.id)
        except Partner.DoesNotExist:
            return None   
        
    @property
    def employee(self):
        from empPortal.model import Employees  # Lazy import inside the method to avoid circular import
        try:
            return Employees.objects.get(user_id=self.id)
        except Employees.DoesNotExist:
            return None  
          
    @property
    def examRes(self):
        try:
            return ExamResult.objects.filter(
                status__in=['passed','failed'],user_id=self.id
                ).order_by('-id').first()
        except ExamResult.DoesNotExist:
            return None 

    @property
    def can_download_certificates(self):
        exam_result = self.examRes
        if exam_result and exam_result.created_at:
           return timezone.now() >= exam_result.created_at + timedelta(days=5)
        return False  

class Franchises(models.Model):
    name = models.CharField(max_length=255, verbose_name="Franchise Name")
    contact_person = models.CharField(max_length=255, verbose_name="Contact Person")
    mobile = models.CharField(max_length=15, verbose_name="Mobile")
    email = models.EmailField(max_length=255, unique=True, verbose_name="Email")
    address = models.TextField(null=True, blank=True, verbose_name="Address")
    city = models.CharField(max_length=100, null=True, blank=True, verbose_name="City")
    state = models.CharField(max_length=100, null=True, blank=True, verbose_name="State")
    pincode = models.CharField(max_length=10, null=True, blank=True, verbose_name="Pincode")
    gst_number = models.CharField(max_length=20, unique=True, null=True, blank=True, verbose_name="GST Number")
    pan_number = models.CharField(max_length=10, unique=True, null=True, blank=True, verbose_name="PAN Number")
    registration_no = models.CharField(max_length=50, unique=True, null=True, blank=True, verbose_name="Registration Number")
    
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Inactive', 'Inactive'),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Active', verbose_name="Status")

    created_at = models.DateTimeField(default=timezone.now, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        db_table = 'franchises'
        verbose_name = "Franchise"
        verbose_name_plural = "Franchises"

    def __str__(self):
        return self.name

    def status_type(self):
        return "Active" if self.status == "Active" else "Inactive"

from django.db import models
from django.utils import timezone

class Department(models.Model):
    name = models.CharField(max_length=255, verbose_name="Department Name")
    head = models.CharField(max_length=255, verbose_name="Head of Department")
    head_of_department = models.CharField(max_length=255, verbose_name="Head of Department Name")  # New Field
    contact_person = models.CharField(max_length=255, verbose_name="Contact Person")  # New Field
    contact_number = models.CharField(max_length=15, verbose_name="Contact Number")
    address = models.TextField(null=True, blank=True, verbose_name="Address")
    city = models.CharField(max_length=100, null=True, blank=True, verbose_name="City")
    state = models.CharField(max_length=100, null=True, blank=True, verbose_name="State")
    pincode = models.CharField(max_length=10, null=True, blank=True, verbose_name="Pincode")
    
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Inactive', 'Inactive'),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Active', verbose_name="Status")

    created_at = models.DateTimeField(default=timezone.now, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        db_table = 'departments'
        verbose_name = "Department"
        verbose_name_plural = "Departments"

    def __str__(self):
        return self.name

    def status_type(self):
        return "Active" if self.status == "Active" else "Inactive"
    
class Franchise(models.Model):
    FRANCHISE_TYPE_CHOICES=(
        ('Corporate','Corporate'),
        ('Individual','Individual')
    )    
    
    CHANNEL_TYPE_CHOICES=(
        ('POSP','POSP'),
        ('Agency','Agency'),
        ('Broker','Broker'),
        ('Sub-Broker','Sub-broker')
    )
    
    STATUS_CHOICES =(
    ('Active', 'Active'),
    ('Inactive', 'Inactive'),
    ('Suspended', 'Suspended'),
    )

    franchise_id = models.CharField(max_length=20, unique=True)
    franchise_code = models.CharField(max_length=20, unique=True)
    franchise_name = models.CharField(max_length=255)
    franchise_type = models.CharField(max_length=20, choices=FRANCHISE_TYPE_CHOICES, null=True, blank=True)
    channel_type = models.CharField(max_length=20, choices=CHANNEL_TYPE_CHOICES)
    franchise_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Active', null=True, blank=True )
    parent_broker_code = models.CharField(max_length=50, blank=True, null=True)
    onboarding_date = models.DateField()

    #  Contact Info fields
    contact_person = models.CharField(max_length=100, blank=True, null=True)
    mobile_number = models.CharField(max_length=15, blank=True, null=True)
    franchise_email = models.EmailField(blank=True, null=True)
    alternate_number = models.CharField(max_length=15, blank=True, null=True)
    designation = models.CharField(max_length=100, blank=True, null=True)

    # Step 3: Address Details fields
    address_line_1 = models.CharField(max_length=255, blank=True, null=True)
    address_line_2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    pincode = models.CharField(max_length=20, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    office_contact_number = models.CharField(max_length=20, blank=True, null=True)

    # Regulatory & Compliance
    pan_number = models.CharField(max_length=20, null=True, blank=True)
    gst_number = models.CharField(max_length=20, null=True, blank=True)
    aadhar_number = models.CharField(max_length=12, null=True, blank=True)

    # Banking & Payout Details
    account_holder_name = models.CharField(max_length=100, null=True, blank=True)
    bank_name           = models.CharField(max_length=100, null=True, blank=True)
    account_number      = models.CharField(max_length=30,  null=True, blank=True)
    ifsc_code           = models.CharField(max_length=11,  null=True, blank=True)
    upi_id              = models.CharField(max_length=100, null=True, blank=True)
    PAYMENT_MODES = [
        ('NEFT', 'NEFT'),
        ('IMPS', 'IMPS'),
        ('UPI',  'UPI'),
    ]
    payment_mode = models.CharField(
                             max_length=4,
                             choices=PAYMENT_MODES,
                             null=True,
                             blank=True
                            )

    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.franchise_name} ({self.franchise_code})"
    
    class Meta:
        db_table="franchise"

class UserFiles(models.Model):
    user = models.ForeignKey('Users', on_delete=models.CASCADE, related_name='files')
    file_url = models.CharField(max_length=255, null=True, blank=True)  
    file_type = models.CharField(max_length=50, null=True, blank=True)  
    file_updated_time = models.DateTimeField(null=True, blank=True)  
    created_at = models.DateTimeField(auto_now_add=True)  

    def __str__(self):
        return f"Files for {self.user.user_name}"

    class Meta:
        db_table = 'user_files'



    # class Meta:
    #     db_table = "commissions"

    # def __str__(self):
    #     return f"Commission {self.id} - Insurer {self.member_id}"
    

class DocumentUpload(models.Model):
    user_id = models.IntegerField()  # Reference to user
    aadhaar_number = models.CharField(max_length=12, unique=True)
    aadhaar_card_front = models.FileField(upload_to='documents/')
    aadhaar_card_front_updated_at = models.DateTimeField(null=True, blank=True)
    aadhaar_card_front_status = models.CharField(
        max_length=10,
        choices=[('Pending', 'Pending'), ('Approved', 'Approved'), ('Rejected', 'Rejected')],
        default='Pending',
        null=True,
        blank=True
    )
    aadhaar_card_front_reject_note = models.CharField(max_length=255, null=True, blank=True)
    aadhaar_card_back = models.FileField(upload_to='documents/')
    aadhaar_card_back_updated_at = models.DateTimeField(null=True, blank=True)
    aadhaar_card_back_status = models.CharField(
        max_length=10,
        choices=[('Pending', 'Pending'), ('Approved', 'Approved'), ('Rejected', 'Rejected')],
        default='Pending',
        null=True,
        blank=True
    )
    aadhaar_card_back_reject_note = models.CharField(max_length=255, null=True, blank=True)
    pan_number = models.CharField(max_length=10, unique=True)
    upload_pan = models.FileField(upload_to='documents/')
    upload_pan_updated_at = models.DateTimeField(null=True, blank=True)
    upload_pan_status = models.CharField(
        max_length=10,
        choices=[('Pending', 'Pending'), ('Approved', 'Approved'), ('Rejected', 'Rejected')],
        default='Pending',
        null=True,
        blank=True
    )
    upload_pan_reject_note = models.CharField(max_length=255, null=True, blank=True)
    cheque_number = models.CharField(max_length=20, unique=True)
    upload_cheque = models.FileField(upload_to='documents/')
    upload_cheque_updated_at = models.DateTimeField(null=True, blank=True)
    upload_cheque_status = models.CharField(
        max_length=10,
        choices=[('Pending', 'Pending'), ('Approved', 'Approved'), ('Rejected', 'Rejected')],
        default='Pending',
        null=True,
        blank=True
    )
    upload_cheque_reject_note = models.CharField(max_length=255, null=True, blank=True)
    role_no = models.CharField(max_length=20, null=True, blank=True)
    tenth_marksheet = models.FileField(upload_to='documents/')
    tenth_marksheet_updated_at = models.DateTimeField(null=True, blank=True)
    tenth_marksheet_status = models.CharField(
        max_length=10,
        choices=[('Pending', 'Pending'), ('Approved', 'Approved'), ('Rejected', 'Rejected')],
        default='Pending',
        null=True,
        blank=True
    )
    tenth_marksheet_reject_note = models.CharField(max_length=255, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Documents for User {self.user_id}"

    class Meta:
        db_table = 'documents_upload'

class UnprocessedPolicyFiles(models.Model):
    policy_document = models.CharField(max_length=255)
    bulk_log_id = models.IntegerField()
    file_path = models.CharField(max_length=255)
    doc_name = models.CharField(max_length=255)
    error_message = models.TextField()
    status = models.CharField(max_length=50, choices=[("Pending", "Pending"), ("Reprocessed", "Reprocessed")], default="Pending")
    created_at = models.DateTimeField(auto_now_add=True)

    def created_date(self):
        return self.created_at.strftime("%d-%m-%Y %H:%M:%S") if self.created_at else None

    class Meta:
        db_table = 'unprocessed_policy_files'


class Exam(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    duration = models.IntegerField(help_text="Duration in minutes")
    exam_eligibility = models.FloatField(null=True, blank=True, help_text="Eligibility score for the exam")
    exam_question_count = models.IntegerField(null=True, blank=True, help_text="Total number of questions in the exam")
    duration = models.IntegerField(help_text="Duration in minutes")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
    
    class Meta:
        db_table = 'exam'
        verbose_name = "Exam"
        verbose_name_plural = "Exams"
        

class Question(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.question_text
    
    class Meta:
        db_table = 'question'
        verbose_name = "Question"
        verbose_name_plural = "Questions"

class Option(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='options')
    option_text = models.TextField()
    is_correct = models.BooleanField(default=False)  # True for the correct option

    def __str__(self):
        return self.option_text
    
    class Meta:
        db_table = 'option'
        verbose_name = "Option"
        verbose_name_plural = "Options"


class UserAnswer(models.Model):
    user = models.ForeignKey(Users, on_delete=models.CASCADE)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_option = models.ForeignKey(Option, on_delete=models.SET_NULL, null=True, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    def is_correct(self):
        return self.selected_option.is_correct if self.selected_option else False

    def __str__(self):
        return f"{self.user.username} - {self.question.question_text}"
    
    class Meta:
        db_table = 'user_answer'
        verbose_name = "user_answers"
        verbose_name_plural = "User_answers"
        

# Exam Results Model (Stores Scores)
class ExamResult(models.Model):
    user = models.ForeignKey(Users, on_delete=models.CASCADE)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    total_questions = models.IntegerField(default=0)
    total_attempted_questions = models.IntegerField(default=0)
    correct_answers = models.IntegerField(default=0)
    percentage = models.DecimalField(max_digits=5, decimal_places=2)
    status = models.CharField(max_length=10, choices=[('passed', 'Passed'), ('failed', 'Failed')], default='failed')
    created_at = models.DateTimeField(auto_now_add=True)
    exam_submitted = models.IntegerField(default=1, help_text="1->start, 2->submitted")

    def __str__(self):
        return f"{self.user.username} - {self.exam.title} - {self.status}"

    class Meta:
        db_table = 'exam_result'
        verbose_name = "Exam_result"
        verbose_name_plural = "Exam_results"
        

class IrdaiAgentApiLogs(models.Model):
    url = models.URLField(null=True, blank=True)
    user_id = models.IntegerField(null=True, blank=True)
    request_payload = models.TextField(null=True, blank=True)
    request_headers = models.TextField(null=True, blank=True)
    response_status = models.IntegerField(null=True, blank=True)
    response_body = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Log {self.id} - {self.url} ({self.response_status})"
    
    class Meta:
        db_table = 'irdai_agent_api_logs'
        

# class UploadedZip(models.Model):
#     file = models.FileField(upload_to='zips/')
#     uploaded_at = models.DateTimeField(auto_now_add=True)
#     campaign_name = models.CharField(max_length=255)
#     rm_id = models.CharField(max_length=100, null=True, blank=True)
#     rm_name = models.CharField(max_length=255, null=True, blank=True)
#     is_processed = models.BooleanField(default=False)
    
#     class Meta:
#         db_table = 'uploaded_zip'


class BulkPolicyLog(models.Model):
    file = models.FileField(upload_to='zips/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    rm_name = models.CharField(max_length=255, null=True, blank=True)
    is_processed = models.BooleanField(default=False)
    camp_name = models.CharField(max_length=255)
    file_name = models.CharField(max_length=255)
    file_url = models.URLField(max_length=255)
    count_total_files = models.IntegerField(default=0) 
    count_not_pdf = models.IntegerField(default=0)
    count_pdf_files = models.IntegerField(default=0)
    count_error_pdf_files = models.IntegerField(default=0)
    count_error_process_pdf_files = models.IntegerField(default=0)
    count_uploaded_files = models.IntegerField(default=0)
    count_duplicate_files = models.IntegerField(default=0)
    status = models.SmallIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)
    rm_id = models.IntegerField(null=True)
    insurance_company_id = models.IntegerField(null=True)
    product_type = models.IntegerField(null=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    def created_date(self):
        return localtime(self.created_at).strftime("%d-%m-%Y %H:%M:%S") if self.created_at else None
    
    def uploaded_date(self):
        return localtime(self.uploaded_at).strftime("%d-%m-%Y %H:%M:%S") if self.uploaded_at else None
    
    class Meta:
        db_table = 'bulk_policy_log'
    
    def save(self, *args, **kwargs):
        if self.file:
            self.file_name = self.file.name
            self.file_url = self.file.url  # Make sure MEDIA_URL is properly set
        super().save(*args, **kwargs)   
        
    def __str__(self):
        return self.file_name or f"Uploaded Zip #{self.pk}"
       
       
class UploadedZip(models.Model):
    file = models.FileField(upload_to='zips/')
    file_name = models.CharField(max_length=255, blank=True)
    file_url = models.URLField(blank=True)
    total_files = models.IntegerField(default=0)
    pdf_files_count = models.IntegerField(default=0)
    non_pdf_files_count = models.IntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    campaign_name = models.CharField(max_length=255)
    rm_id = models.CharField(max_length=100, null=True, blank=True)
    rm_name = models.CharField(max_length=255, null=True, blank=True)
    is_processed = models.BooleanField(default=False)
    bulk_log = models.ForeignKey(BulkPolicyLog, on_delete=models.CASCADE)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    class Meta:
        db_table = 'uploaded_zip'

    def save(self, *args, **kwargs):
        if self.file:
            self.file_name = self.file.name
            self.file_url = self.file.url  # Make sure MEDIA_URL is properly set
        super().save(*args, **kwargs)

    def __str__(self):
        return self.file_name or f"Uploaded Zip #{self.pk}"
     
class ExtractedFile(models.Model):
    bulk_log_ref = models.ForeignKey(BulkPolicyLog, on_delete=models.CASCADE)
    # zip_ref = models.ForeignKey(UploadedZip, on_delete=models.CASCADE)
    file_path = models.FileField(upload_to='pdf_files/')
    filename = models.CharField(max_length=255)
    content = models.TextField(blank=True, null=True)
    source_id = models.CharField(max_length=255, null=True, blank=True)
    is_uploaded = models.BooleanField(default=False)
    is_extracted = models.BooleanField(default=False)
    is_failed = models.BooleanField(default=False)
    chat_response = models.TextField(null=True, blank=True)
    extracted_at = models.DateTimeField(auto_now_add=True)
    policy = models.ForeignKey(PolicyDocument, on_delete=models.CASCADE)
    file_url = models.URLField(blank=True, null=True)
    status = models.IntegerField(default=0)
    retry_source_count = models.IntegerField(default=0)
    retry_chat_response_count = models.IntegerField(default=0)
    retry_creating_policy_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return self.filename
    
    class Meta:
        db_table = 'extracted_file'
        
class SingleUploadFile(models.Model):
    file_path = models.FileField(upload_to='pdf_files/')
    filename = models.CharField(max_length=255)
    product_type = models.IntegerField()
    content = models.TextField(blank=True, null=True)
    source_id = models.CharField(max_length=255, null=True, blank=True)
    is_uploaded = models.BooleanField(default=False)
    is_extracted = models.BooleanField(default=False)
    chat_response = models.TextField(null=True, blank=True)
    extracted_at = models.DateTimeField(auto_now_add=True)
    policy = models.ForeignKey(PolicyDocument, on_delete=models.SET_NULL, null=True, blank=True)
    file_url = models.URLField(blank=True, null=True)
    status = models.IntegerField(default=0)
    retry_source_count = models.IntegerField(default=0)
    retry_chat_response_count = models.IntegerField(default=0)
    retry_creating_policy_count = models.IntegerField(default=0)
    is_completed = models.BooleanField(default=False)
    is_failed = models.BooleanField(default=False)
    insurance_company_id = models.IntegerField(null=True)
    

    upload_at = models.DateTimeField(default=timezone.now)
    create_by = models.ForeignKey(Users, on_delete=models.SET_NULL, null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.file_path:
            self.filename = self.file_path.name
            self.file_url = self.file_path.url  # Assumes MEDIA_URL and MEDIA_ROOT properly set
        super().save(*args, **kwargs)
        
    def __str__(self):
        return self.filename

    class Meta:
        db_table = 'single_upload_file'
        
class FileAnalysis(models.Model):
    zip = models.ForeignKey(UploadedZip, on_delete=models.CASCADE)
    filename = models.CharField(max_length=255)
    extracted_text = models.TextField()
    extracted_file = models.ForeignKey(ExtractedFile, on_delete=models.CASCADE)
    policy = models.ForeignKey(PolicyDocument, on_delete=models.CASCADE)
    gpt_response = models.JSONField()
    status = models.CharField(max_length=50, default="pending")
    
    class Meta:
        db_table = 'file_analysis'
        
class ChatGPTLog(models.Model):
    prompt = models.TextField()
    response = models.TextField(blank=True, null=True)
    status_code = models.IntegerField(null=True, blank=True)
    is_successful = models.BooleanField(default=False)
    error_message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"ChatGPT Log - {self.created_at}"
    
    class Meta:
        db_table = 'chatgptlog'
        managed = True
        verbose_name = 'ChatGPTLog'
        verbose_name_plural = 'ChatGPTLogs'
        
class UploadedExcel(models.Model):
    file = models.FileField(upload_to='excels/')
    file_name = models.CharField(max_length=255, blank=True)
    file_url = models.URLField(blank=True)
    total_rows = models.IntegerField(default=0)
    error_rows = models.IntegerField(default=0)
    success_rows = models.IntegerField(default=0)
    valid_rows = models.IntegerField(default=0)
    invalid_rows = models.IntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    campaign_name = models.CharField(max_length=255)
    is_processed = models.BooleanField(default=False)
    error = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    class Meta:
        db_table = 'uploaded_excels'

    def save(self, *args, **kwargs):
        if self.file:
            self.file_name = self.file.name
            self.file_url = self.file.url  # Make sure MEDIA_URL is properly set
        super().save(*args, **kwargs)

    def __str__(self):
        return self.file_name or f"Uploaded Excel #{self.pk}"
   
class PolicyInfoLog(models.Model):
    policy_info = models.ForeignKey(PolicyInfo,on_delete=models.CASCADE,related_name='policy_info_log')
    log_policy = models.ForeignKey(PolicyDocument,on_delete=models.CASCADE,related_name='policy_info_policyDocument_logs')
    log_policy_number = models.CharField(max_length=100, null=True, blank=True)
    log_policy_issue_date = models.CharField(max_length=35, null=True, blank=True)
    log_policy_start_date = models.CharField(max_length=35, null=True, blank=True)
    log_policy_expiry_date = models.CharField(max_length=35, null=True, blank=True)
    log_insurer_name = models.CharField(max_length=255, null=True, blank=True)
    log_insured_mobile = models.CharField(max_length=15, null=True, blank=True)
    log_insured_email = models.CharField(max_length=255, null=True, blank=True)
    log_insured_address = models.TextField(null=True, blank=True)
    log_insured_pan = models.CharField(max_length=20, null=True, blank=True)
    log_insured_aadhaar = models.CharField(max_length=20, null=True, blank=True)
    log_insurance_company = models.CharField(max_length=255, null=True, blank=True)
    log_service_provider = models.CharField(max_length=255, null=True, blank=True)
    log_insurer_contact_name = models.CharField(max_length=255, null=True, blank=True)
    log_bqp = models.CharField(max_length=255, null=True, blank=True)
    log_pos_name = models.CharField(max_length=255, null=True, blank=True)
    log_referral_by = models.CharField(max_length=50, null=True, blank=True)
    log_branch_name = models.CharField(max_length=255, null=True, blank=True)
    log_supervisor_name = models.CharField(max_length=255, null=True, blank=True)
    log_policy_type = models.CharField(max_length=255, null=True, blank=True)
    log_policy_plan = models.CharField(max_length=255, null=True, blank=True)
    log_sum_insured = models.CharField(max_length=20, null=True, blank=True)
    log_od_premium = models.CharField(max_length=20, null=True, blank=True)
    log_tp_premium = models.CharField(max_length=20, null=True, blank=True)
    log_pa_count = models.CharField(max_length=20, default='0', null=True, blank=True)
    log_pa_amount = models.CharField(max_length=20, null=True, blank=True)
    log_driver_count = models.CharField(max_length=20, null=True, blank=True)
    log_driver_amount = models.CharField(max_length=20, null=True, blank=True)
    log_fuel_type = models.CharField(max_length=50, null=True, blank=True)
    log_be_fuel_amount = models.CharField(max_length=50, null=True, blank=True)
    log_gross_premium = models.CharField(max_length=50, null=True, blank=True)
    log_net_premium = models.CharField(max_length=50, null=True, blank=True)
    log_active = models.BooleanField(default=True)
    action = models.CharField(max_length=10, choices=[('insert', 'Insert'), ('update', 'Update')])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'policy_info_log'
        verbose_name = 'Policy Info Log'
        verbose_name_plural = 'Policy Info Logs'

    def __str__(self):
        return f"Policy Info Log for Policy #{self.log_policy_number}"

class PolicyVehicleInfoLog(models.Model):
    policy_vehicle_info = models.ForeignKey(PolicyVehicleInfo,on_delete=models.CASCADE,related_name='policy_vehicle_info_log')
    log_policy_document = models.ForeignKey(PolicyDocument,on_delete=models.CASCADE,related_name='policy_vehicle_info_policyDocument_logs')
    log_policy_number = models.CharField(max_length=100)
    log_vehicle_type = models.CharField(max_length=100, null=True, blank=True)
    log_vehicle_make = models.CharField(max_length=100, null=True, blank=True)
    log_vehicle_model = models.CharField(max_length=100, null=True, blank=True)
    log_vehicle_variant = models.CharField(max_length=100, null=True, blank=True)
    log_fuel_type = models.CharField(max_length=30, null=True, blank=True)  # Originally ENUM('Petrol', 'Diesel')
    log_gvw = models.CharField(max_length=50, null=True, blank=True)
    log_cubic_capacity = models.CharField(max_length=50, null=True, blank=True)
    log_seating_capacity = models.CharField(max_length=10, null=True, blank=True)
    log_registration_number = models.CharField(max_length=100, null=True, blank=True)
    log_engine_number = models.CharField(max_length=100, null=True, blank=True)
    log_chassis_number = models.CharField(max_length=100, null=True, blank=True)
    log_manufacture_year = models.CharField(max_length=4, null=True, blank=True)
    log_active = models.BooleanField(default=True)
    action = models.CharField(max_length=10, choices=[('insert', 'Insert'), ('update', 'Update')])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'policy_vehicle_info_log'
        verbose_name = 'Policy Vehicle Info Log'
        verbose_name_plural = 'Policy Vehicle Info Logs'

    def __str__(self):
        return f"Policy Vehicle Info Log for Policy #{self.log_policy_number}"

class InsurerPaymentDetailsLog(models.Model):
    insurer_payment = models.ForeignKey(InsurerPaymentDetails,on_delete=models.CASCADE,related_name='insurer_payment_log')
    log_policy_document = models.ForeignKey(PolicyDocument,on_delete=models.CASCADE,related_name='insurer_policyDocument_logs')
    log_policy_number = models.CharField(max_length=100)
    log_insurer_payment_mode = models.CharField(max_length=100, blank=True, null=True)
    log_insurer_payment_date = models.CharField(max_length=100, blank=True, null=True)
    log_insurer_amount = models.CharField(max_length=50, blank=True, null=True)
    log_insurer_remarks = models.TextField(blank=True, null=True)
    log_insurer_od_comm = models.CharField(max_length=50, blank=True, null=True)
    log_insurer_net_comm = models.CharField(max_length=50, blank=True, null=True)
    log_insurer_tp_comm = models.CharField(max_length=50, blank=True, null=True)
    log_insurer_incentive_amount = models.CharField(max_length=50, blank=True, null=True)
    log_insurer_tds = models.CharField(max_length=50, blank=True, null=True)
    log_insurer_od_amount = models.CharField(max_length=50, blank=True, null=True)
    log_insurer_net_amount = models.CharField(max_length=50, blank=True, null=True)
    log_insurer_tp_amount = models.CharField(max_length=50, blank=True, null=True)
    log_insurer_total_comm_amount = models.CharField(max_length=50, blank=True, null=True)
    log_insurer_net_payable_amount = models.CharField(max_length=50, blank=True, null=True)
    log_insurer_tds_amount = models.CharField(max_length=50, blank=True, null=True)
    log_insurer_total_commission = models.CharField(max_length=50, blank=True, null=True)
    log_insurer_receive_amount = models.CharField(max_length=50, blank=True, null=True)
    log_insurer_balance_amount = models.CharField(max_length=50, blank=True, null=True)
    log_active = models.BooleanField(default=True)
    action = models.CharField(max_length=10, choices=[('insert', 'Insert'), ('update', 'Update')])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'insurer_payment_details_log'
        verbose_name = 'Insurance Payment Details Log'
        verbose_name_plural = 'Insurance Payment Details Logs'

    def __str__(self):
        return f"Insurance Payment Details Log for Policy #{self.log_policy_number}"

class FranchisePaymentLog(models.Model):
    franchise_payment = models.ForeignKey(FranchisePayment,on_delete=models.CASCADE,related_name='logs')
    log_policy_document = models.ForeignKey(PolicyDocument,on_delete=models.CASCADE,related_name='payment_logs')
    log_policy_number = models.CharField(max_length=50)
    log_franchise_od_comm = models.CharField(max_length=50, blank=True, null=True)
    log_franchise_net_comm = models.CharField(max_length=50, blank=True, null=True)
    log_franchise_tp_comm = models.CharField(max_length=50, blank=True, null=True)
    log_franchise_incentive_amount = models.CharField(max_length=50, blank=True, null=True)
    log_franchise_tds = models.CharField(max_length=50, blank=True, null=True)
    log_franchise_od_amount = models.CharField(max_length=50, blank=True, null=True)
    log_franchise_net_amount = models.CharField(max_length=50, blank=True, null=True)
    log_franchise_tp_amount = models.CharField(max_length=50, blank=True, null=True)
    log_franchise_total_comm_amount = models.CharField(max_length=50, blank=True, null=True)
    log_franchise_net_payable_amount = models.CharField(max_length=50, blank=True, null=True)
    log_franchise_tds_amount = models.CharField(max_length=50, blank=True, null=True)
    log_active = models.BooleanField(default=True)
    action = models.CharField(max_length=10, choices=[('insert', 'Insert'), ('update', 'Update')])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'franchise_payment_logs'
        verbose_name = 'Franchise Payment Log'
        verbose_name_plural = 'Franchise Payment Logs'

    def __str__(self):
        return f"Franchise Payment Log for Policy #{self.log_policy_number}"

class AgentPaymentDetailsLog(models.Model):
    agent_payment = models.ForeignKey(AgentPaymentDetails,on_delete=models.CASCADE,related_name='agent_payment_log')
    log_policy_document = models.ForeignKey(PolicyDocument,on_delete=models.CASCADE,related_name='agent_policyDocument_logs')
    log_policy_number = models.CharField(max_length=255)
    log_agent_name = models.CharField(max_length=255)
    log_agent_payment_mod = models.CharField(max_length=255)
    log_transaction_id = models.CharField(max_length=255)
    log_agent_payment_date = models.CharField(max_length=255)
    log_agent_amount = models.CharField(max_length=255)
    log_agent_remarks = models.CharField(max_length=255)
    log_agent_od_comm = models.CharField(max_length=255)
    log_agent_tp_comm = models.CharField(max_length=255)
    log_agent_net_comm = models.CharField(max_length=255)
    log_agent_incentive_amount = models.CharField(max_length=255)
    log_agent_tds = models.CharField(max_length=255)
    log_agent_od_amount = models.CharField(max_length=255)
    log_agent_net_amount = models.CharField(max_length=255)
    log_agent_tp_amount = models.CharField(max_length=255)
    log_agent_total_comm_amount = models.CharField(max_length=255)
    log_agent_net_payable_amount = models.CharField(max_length=255)
    log_agent_tds_amount = models.CharField(max_length=255)
    log_active = models.BooleanField(default=True)
    action = models.CharField(max_length=10, choices=[('insert', 'Insert'), ('update', 'Update')])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'agent_payment_details_log'
        verbose_name = 'Agent Payment Details Log'
        verbose_name_plural = 'Agent Payment Details Logs'

    def __str__(self):
        return f"Agent Payment Details Log for Policy #{self.log_policy_number}"
    
### Upload Referral Excel ###

class RefUploadedExcel(models.Model):
    file = models.FileField(upload_to='excels/')
    file_name = models.CharField(max_length=255, blank=True)
    file_url = models.URLField(blank=True)
    total_rows = models.IntegerField(default=0)
    error_rows = models.IntegerField(default=0)
    success_rows = models.IntegerField(default=0)
    valid_rows = models.IntegerField(default=0)
    invalid_rows = models.IntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    # campaign_name = models.CharField(max_length=255)
    is_processed = models.BooleanField(default=False)
    error = models.TextField(blank=True)
    created_by = models.ForeignKey(
        Users,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    class Meta:
        db_table = 'ref_upload_excels'    


class PartnerUploadExcel(models.Model):
    file = models.FileField(upload_to="partner_excels/")
    file_name = models.CharField(max_length=255, default="")
    file_url = models.CharField(max_length=200, default="")
    total_rows = models.IntegerField(default=0)
    error_rows = models.IntegerField(default=0)
    success_rows = models.IntegerField(default=0)
    valid_rows = models.IntegerField(default=0)
    invalid_rows = models.IntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_processed = models.BooleanField(default=False)
    error = models.TextField(default="")
    created_by = models.ForeignKey(Users, on_delete=models.SET_NULL, null=True)
    class Meta:
        db_table = 'partner_upload_excels'
        

class InsurerBulkUpload(models.Model):
    campaign_name = models.CharField(max_length=255)
    file = models.FileField(upload_to="insurer_excels/")
    file_name = models.CharField(max_length=255, default="")
    file_url = models.CharField(max_length=200, default="")
    total_rows = models.IntegerField(default=0)
    error_rows = models.IntegerField(default=0)
    success_rows = models.IntegerField(default=0)
    valid_rows = models.IntegerField(default=0)
    invalid_rows = models.IntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_processed = models.BooleanField(default=False)
    error = models.TextField(default="")
    created_by = models.ForeignKey(Users, on_delete=models.SET_NULL, null=True)

    class Meta:
        db_table = 'insurer_bulk_uploads'

class LeadUploadExcel(models.Model):
    file = models.FileField(upload_to="lead_excels/")
    file_name = models.CharField(max_length=255, default='')
    file_url = models.CharField(max_length=200, default='')
    total_rows = models.IntegerField(default=0)
    error_rows = models.IntegerField(default=0)
    success_rows = models.IntegerField(default=0)
    valid_rows = models.IntegerField(default=0)
    invalid_rows = models.IntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_processed = models.BooleanField(default=False)
    error = models.TextField(default='', blank=True)
    campaign_name = models.CharField(max_length=255, default='', blank=True)

    created_by = models.ForeignKey(
        Users, 
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        db_column='created_by_id' 
    )
    class Meta:
        db_table = 'lead_upload_excels'
    

    
class InsurerBulkUploadPolicyLog(models.Model):
    STATUS_CHOICES = [
        ('success', 'Success'),
        ('failed', 'Failed'),
    ]
    upload = models.ForeignKey('InsurerBulkUpload', on_delete=models.CASCADE, related_name="logs")
    policy_number = models.CharField(max_length=100)
    status = models.CharField(max_length=7, choices=STATUS_CHOICES)
    message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.policy_number} - {self.status}"

    class Meta:
        db_table = 'insurer_bulk_upload_policy_log'


        
class QuotationFormData(models.Model):
    customer_id = models.CharField(max_length=100, blank=True, null=True)
    form_data = models.TextField()  # LONGTEXT in MySQL
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Form Data for {self.customer_id} on {self.created_at.strftime('%Y-%m-%d')}"
    
    class Meta:
        db_table = 'quotation_form_data'  # Matches your MySQL table name
