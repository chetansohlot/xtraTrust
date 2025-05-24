from django.db import models
from django.conf import settings
import uuid
from empPortal.model.wimGmcPolicyInfo import WimGmcPolicyInfo

class GmcPolicyCoverage(models.Model):
    coverage_ref_id = models.CharField(max_length=100,null=True,blank=True)
    
    policy = models.ForeignKey(
        WimGmcPolicyInfo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    coverage_item = models.CharField(max_length=100,null=True,blank=True)
    coverage_description = models.TextField()
    sum_insured = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    status = models.BooleanField(default=True)  # TINYINT(1) used for boolean
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='coverages_created'
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='coverages_updated'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'gmc_policy_coverages'

    def __str__(self):
        return f"{self.coverage_item} - {self.coverage_description[:30]}..."
    
    def save(self, *args, **kwargs):
        if not self.coverage_ref_id:
            self.coverage_ref_id = f"COVG-{uuid.uuid4().hex[:10].upper()}"
        super().save(*args, **kwargs)
