from django.db import models

class WimMasterTPA(models.Model):
    master_tpa_name = models.CharField(max_length=75, null=True, blank=True)
    master_tpa_short_name = models.CharField(max_length=75, null=True, blank=True)
    master_tpa_phone_number = models.CharField(max_length=15, null=True, blank=True)
    master_tpa_email = models.CharField(max_length=75, null=True, blank=True)
    master_tpa_address = models.TextField(null=True, blank=True)
    master_tpa_is_active = models.BooleanField(default=True)  # 1->Active, 0->Inactive
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'wim_master_tpas'  # to match your MySQL table name

    def __str__(self):
        return self.master_tpa_name or "Unnamed TPA"
