from django.db import models
from ..models import Leads  
from empPortal.model import Insurance
from empPortal.model.vehicleTypes import VehicleType
from empPortal.model.policyTypes import PolicyType

class LeadPreviousPolicy(models.Model):
    lead = models.ForeignKey(Leads, on_delete=models.SET_NULL, null=True, blank=True,related_name='pk_lead_details')
    registration_number = models.CharField(max_length=50, null=True, blank=True)
    registration_date = models.DateField(null=True, blank=True)
    vehicle_type = models.ForeignKey(VehicleType, on_delete=models.SET_NULL,null=True,blank=True)
    make = models.CharField(max_length=100, null=True, blank=True)
    model = models.CharField(max_length=100, null=True, blank=True)
    variant = models.CharField(max_length=100, null=True, blank=True)
    year_of_manufacture = models.IntegerField(null=True, blank=True)
    registration_state = models.CharField(max_length=50, null=True, blank=True)
    registration_city = models.CharField(max_length=100, null=True, blank=True)
    chassis_number = models.CharField(max_length=100, null=True, blank=True)
    engine_number = models.CharField(max_length=100, null=True, blank=True)
    claim_history = models.BooleanField(null=True, blank=True)
    ncb = models.BooleanField(null=True, blank=True)
    ncb_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    idv_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    policy_type = models.ForeignKey(PolicyType,on_delete=models.SET_NULL,null=True,blank=True,related_name="pk_policy_type")
    policy_duration = models.CharField(max_length=50, null=True, blank=True)
    addons = models.TextField(null=True, blank=True)
    owner_name = models.CharField(max_length=100, null=True, blank=True)
    father_name = models.CharField(max_length=100, null=True, blank=True)
    state_code = models.CharField(max_length=10, null=True, blank=True)
    location = models.CharField(max_length=100, null=True, blank=True)
    vehicle_category = models.CharField(max_length=100, null=True, blank=True)
    vehicle_class_description = models.CharField(max_length=100, null=True, blank=True)
    body_type_description = models.CharField(max_length=100, null=True, blank=True)
    vehicle_color = models.CharField(max_length=50, null=True, blank=True)
    vehicle_cubic_capacity = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    vehicle_gross_weight = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    vehicle_seating_capacity = models.IntegerField(null=True, blank=True)
    vehicle_fuel_description = models.CharField(max_length=50, null=True, blank=True)
    vehicle_owner_number = models.IntegerField(null=True, blank=True)
    rc_expiry_date = models.DateField(null=True, blank=True)
    rc_pucc_expiry_date = models.DateField(null=True, blank=True)
    insurance_company = models.ForeignKey(Insurance, on_delete=models.SET_NULL, null=True, blank=True)
    insurance_expiry_date = models.DateField(null=True, blank=True)
    insurance_policy_number = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f"{self.registration_number or 'Unknown'} - {self.owner_name or 'Unknown'}"
    
    class Meta:
        db_table = 'lead_previous_policy'    
