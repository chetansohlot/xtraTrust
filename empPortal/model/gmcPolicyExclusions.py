from django.db import models
from django.conf import settings
import uuid
from empPortal.model.wimGmcPolicyInfo import WimGmcPolicyInfo

class GmcPolicyExclusions(models.Model):
    exclusion_ref_id = models.CharField(max_length=100,null=True,blank=True)
    policy = models.ForeignKey(
        WimGmcPolicyInfo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    exclusion_title = models.CharField(max_length=255,null=True,blank=True)
    exclusion_description = models.TextField()
    status = models.BooleanField(default=True)  # TINYINT(1) used for boolean
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='exclusions_created'
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='exclusions_updated'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'gmc_policy_exclusions'

    def __str__(self):
        return f"{self.exclusion_title} - {self.exclusion_description[:30]}..."
    
    def save(self, *args, **kwargs):
        if not self.exclusion_ref_id:
            self.exclusion_ref_id = f"EXL-{uuid.uuid4().hex[:10].upper()}"
        super().save(*args, **kwargs)
