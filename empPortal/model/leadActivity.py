from django.db import models
from django.contrib.auth.models import User
from empPortal.model.Dispositions import Disposition, SubDisposition
from ..models import Leads
from datetime import datetime
from django.conf import settings
from django.utils.timezone import localtime
from django.utils import timezone
import pytz
INDIA_TZ = pytz.timezone('Asia/Kolkata')

class LeadActivity(models.Model):
    id = models.BigAutoField(primary_key=True)
    lead = models.ForeignKey(Leads,on_delete=models.SET_NULL,null=True,blank=True,related_name='activity_for_lead_id')
    lead_ref_id = models.CharField(max_length=255,null=True,blank=True)
    message = models.TextField(null=True,blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='activity_created_by', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Lead Activity #{self.id} for Lead {self.lead_id}" if self.lead_id else f"Lead Activity #{self.id}"
    
    class Meta:
        db_table = 'lead_activity'    
        
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
       
