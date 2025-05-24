from django.db import models
from django.conf import settings
import uuid
from empPortal.model.wimGmcPolicyInfo import WimGmcPolicyInfo

class GmcPolicyHighlights(models.Model):
    CATEGORY_CHOICES = [
        ('General', 'General'),
        ('Coverage', 'Coverage'),
        ('Benefits', 'Benefits'),
    ]

    highlight_ref_id = models.CharField(max_length=100,null=True,blank=True)
    policy = models.ForeignKey(
        WimGmcPolicyInfo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    category = models.CharField(
        max_length=100,
        choices=CATEGORY_CHOICES,
        default='General'
    )
    highlight = models.TextField()
    status = models.BooleanField(default=True)  # TINYINT(1) used for boolean
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='highlights_created'
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='highlights_updated'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'gmc_policy_highlights'

    def __str__(self):
        return f"{self.category} - {self.highlight[:30]}..."
    
    def save(self, *args, **kwargs):
        if not self.highlight_ref_id:
            self.highlight_ref_id = f"HLG-{uuid.uuid4().hex[:10].upper()}"
        super().save(*args, **kwargs)
