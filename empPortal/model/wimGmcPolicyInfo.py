from django.db import models

import uuid
from empPortal.model.clients import XtClientsBasicInfo
from empPortal.model.wimMasterPolicyTypes import MasterPolicyType
from empPortal.model.insurer import WimMasterInsurer
from empPortal.model.tpas import WimMasterTPA

class WimGmcPolicyInfo(models.Model):
    gmc_reference_id = models.CharField(max_length=100,null=True,blank=True)
    client = models.ForeignKey(XtClientsBasicInfo,on_delete=models.SET_NULL,null=True,blank=True)
    master_insurer = models.ForeignKey(WimMasterInsurer,on_delete=models.SET_NULL,null=True,blank=True)
    master_tpa = models.ForeignKey(WimMasterTPA,on_delete=models.SET_NULL,null=True,blank=True)
    master_policy_type = models.ForeignKey(MasterPolicyType,on_delete=models.SET_NULL,null=True,blank=True)
    gmc_policy_number = models.CharField(max_length=100)
    gmc_product_name = models.CharField(max_length=150)
    gmc_claim_process_mode = models.CharField(max_length=100)
    gmc_policy_start_date = models.DateField()
    gmc_policy_end_date = models.DateField()
    gmc_policy_term_months = models.IntegerField()
    gmc_policy_total_sum_insured = models.DecimalField(max_digits=18, decimal_places=2)
    gmc_policy_premium_amount = models.DecimalField(max_digits=18, decimal_places=2)
    gmc_policy_gst_amount = models.DecimalField(max_digits=18, decimal_places=2)
    gmc_policy_total_lives = models.IntegerField()
    gmc_policy_total_employees = models.IntegerField()
    gmc_policy_total_dependents = models.IntegerField()
    gmc_policy_total_spouses = models.IntegerField()
    gmc_policy_total_childs = models.IntegerField()
    gmc_policy_remarks = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'wim_gmc_policy_info'

    def __str__(self):
        return f"{self.gmc_product_name} - {self.created_at}"
    
    def save(self, *args, **kwargs):
        if not self.gmc_reference_id:
            self.gmc_reference_id = f"GMC-{uuid.uuid4().hex[:10].upper()}"
        super().save(*args, **kwargs)
