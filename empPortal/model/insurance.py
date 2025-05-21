from django.db import models
from empPortal.model.StateCity import State,City

class Insurance(models.Model):
    ACTIVE_CHOICES = [
        ('Inactive', 'Inactive'),
        ('Active', 'Active'),
    ]

    insurance_company = models.CharField(max_length=255)
    ins_short_name =models.CharField(max_length=50)
    #active = models.CharField(max_length=1, choices=ACTIVE_CHOICES, default='1')
    active = models.CharField(max_length=8, choices=ACTIVE_CHOICES, default='Active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    pincode = models.IntegerField(null=True, blank=True, db_column='insurance_type_pincode')
    address = models.TextField(null=True, blank=True, db_column='insurance_type_address')
    commencement_date = models.DateField(null=True, blank=True, db_column='insurance_type_commencement_date')
    #state = models.ForeignKey(State, on_delete=models.SET_NULL, null=True, blank=True, db_column='insurance_type_state')
    #city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True, blank=True, db_column='insurance_type_city')
    state = models.CharField(max_length=100, null=True, blank=True, db_column='insurance_type_state')
    city = models.CharField(max_length=100, null=True, blank=True, db_column='insurance_type_city')
    billing_state = models.CharField(max_length=100, null=True, blank=True)
    billing_city = models.CharField(max_length=100, null=True, blank=True)
    #billing_state = models.ForeignKey(State, on_delete=models.SET_NULL, null=True, blank=True, related_name='billing_states')
    #billing_city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True, blank=True, related_name='billing_cities')
    billing_pincode = models.IntegerField(null=True, blank=True)
    billing_address = models.TextField(null=True, blank=True)
    billing_same_as_registered = models.BooleanField(default=False)  
     # Primary Contact Person Details
    primary_contact_name = models.CharField(max_length=255, null=True, blank=True)
    primary_designation = models.CharField(max_length=255, null=True, blank=True)
    primary_contact_no = models.BigIntegerField(null=True, blank=True)
    primary_contact_email = models.CharField(max_length=255, null=True, blank=True)

    # Secondary Contact Person Details
    secondary_contact_name = models.CharField(max_length=255, null=True, blank=True)
    secondary_designation = models.CharField(max_length=255, null=True, blank=True)
    secondary_contact_no = models.BigIntegerField(null=True, blank=True)
    secondary_contact_email = models.CharField(max_length=255, null=True, blank=True)


    def __str__(self):
        return self.insurance_company
    class Meta:
        db_table = 'insurance_companies'
