from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
import uuid

class Disposition(models.Model):
    disp_id = models.BigAutoField(primary_key=True)
    disp_ref_id = models.CharField(max_length=255, null=True, blank=True)
    disp_name = models.CharField(max_length=255, null=True, blank=True)
    disp_is_active = models.BooleanField(default=True)
    disp_created_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='dispositions_created_by', on_delete=models.SET_NULL, null=True, blank=True)
    disp_updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='dispositions_updated_by', on_delete=models.SET_NULL, null=True, blank=True)
    disp_created_at = models.DateTimeField(auto_now_add=True)
    disp_updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.disp_name or f"Disposition {self.disp_ref_id}"
    
    class Meta:
        db_table = 'dispositions'    
        
        
class SubDisposition(models.Model):
    sub_disp_id = models.BigAutoField(primary_key=True)
    sub_disp_ref_id = models.CharField(max_length=255, null=True, blank=True)
    sub_disp_fk_disp = models.ForeignKey(Disposition, related_name='sub_dispositions_for', on_delete=models.SET_NULL, null=True, blank=True)
    sub_disp_name = models.CharField(max_length=255, null=True, blank=True)
    sub_disp_is_active = models.BooleanField(default=True)
    sub_disp_created_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='sub_dispositions_created_by', on_delete=models.SET_NULL, null=True, blank=True)
    sub_disp_updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='sub_dispositions_updated_by', on_delete=models.SET_NULL, null=True, blank=True)
    sub_disp_created_at = models.DateTimeField(auto_now_add=True)
    sub_disp_updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.sub_disp_name or f"Sub Disposition {self.sub_disp_ref_id}"
    
    class Meta:
        db_table = 'sub_dispositions'
