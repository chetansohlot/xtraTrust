from django.db import models
from django.contrib.auth.models import User
from datetime import datetime
from django.conf import settings
from django.utils.timezone import localtime
from django.utils import timezone
import pytz
INDIA_TZ = pytz.timezone('Asia/Kolkata')

def generate_customer_id():
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"{settings.CUSTOMER_PREFIX}{timestamp}"

class Customer(models.Model):
    customer_id = models.CharField(max_length=20, unique=True)  # For values like CUS2343545
    mobile_number = models.BigIntegerField(null=True, blank=True)
    email_address = models.CharField(max_length=255, null=True, blank=True)
    name_as_per_pan = models.CharField(max_length=255, null=True, blank=True)
    pan_card_number = models.CharField(max_length=10, null=True, blank=True)
    identity_no = models.CharField(max_length=255, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    state = models.CharField(max_length=100, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    pincode = models.CharField(max_length=10, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    created_from = models.CharField(max_length=100,null=True, blank=True)  # quote, lead, direct, policy
    active = models.BooleanField(default=True)  # 1 for active, 0 for inactive
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = "customers"

    def __str__(self):
        return f"Customer {self.customer_id} - {self.name_as_per_pan}"   
        
    def save(self, *args, **kwargs):
        if not self.customer_id:
            self.customer_id = generate_customer_id()
        super().save(*args, **kwargs)
        
    @property
    def create_date(self):
        if self.created_at:
            local_time = timezone.localtime(self.created_at, INDIA_TZ)
            return local_time.strftime("%d %b")
        return None

    @property
    def create_time(self):
        if self.created_at:
            local_time = timezone.localtime(self.created_at, INDIA_TZ)
            return local_time.strftime("%I:%M %p")
        return None
       
