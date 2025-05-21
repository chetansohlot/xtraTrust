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

class LeadDisposition(models.Model):
    id = models.BigAutoField(primary_key=True)
    lead = models.ForeignKey(Leads, on_delete=models.SET_NULL, null=True, blank=True,related_name='lead_disposition')
    disp = models.ForeignKey(Disposition, on_delete=models.SET_NULL, null=True, blank=True,related_name='lead_disposition_id')
    sub_disp = models.ForeignKey(SubDisposition, on_delete=models.SET_NULL, null=True, blank=True,related_name='lead_sub_disposition_id')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='lead_dispositions_created_by', on_delete=models.SET_NULL, null=True, blank=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='lead_dispositions_updated_by', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.IntegerField(default=1)
    followup_date = models.DateField(null=True, blank=True)
    followup_time = models.TimeField(null=True, blank=True)
    remark = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.id or f"Lead Disposition for {self.lead_id}"
    
    class Meta:
        db_table = 'leads_disposition'    
        

class LeadDispositionLogs(models.Model):
    id = models.BigAutoField(primary_key=True)
    log_lead_disp = models.ForeignKey(LeadDisposition,on_delete=models.SET_NULL,null=True,blank=True,related_name="log_lead_disp_id")
    log_lead = models.ForeignKey(Leads, on_delete=models.SET_NULL, null=True, blank=True,related_name='log_lead_disposition')
    log_disp = models.ForeignKey(Disposition, on_delete=models.SET_NULL, null=True, blank=True,related_name='log_lead_disposition_id')
    log_sub_disp = models.ForeignKey(SubDisposition, on_delete=models.SET_NULL, null=True, blank=True,related_name='log_lead_sub_disposition_id')
    log_created_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='log_lead_dispositions_created_by', on_delete=models.SET_NULL, null=True, blank=True)
    log_status = models.IntegerField(default=1)
    log_followup_date = models.DateField(null=True, blank=True)
    log_followup_time = models.TimeField(null=True, blank=True)
    log_remark = models.TextField(null=True, blank=True)
    log_created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Lead Disposition Log #{self.id} for Lead {self.log_lead_id}" if self.log_lead_id else f"Lead Disposition Log #{self.id}"
    
    class Meta:
        db_table = 'leads_disposition_logs'    
        
    @property
    def create_date(self):
        if self.log_created_at:
            local_time = timezone.localtime(self.log_created_at, INDIA_TZ)
            return local_time.strftime("%d %b")
        return None

    @property
    def create_time(self):
        if self.log_created_at:
            local_time = timezone.localtime(self.log_created_at, INDIA_TZ)
            return local_time.strftime("%I:%M %p")
        return None
       
