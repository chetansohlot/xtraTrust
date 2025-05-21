from django.db import models
from django.conf import settings
 
class CommissionUpdateLog(models.Model):
    COMMISSION_TYPE_CHOICES = [
        ('agent', 'Agent'),
        ('franchise', 'Franchise'),
        ('insurer', 'Insurer'),
    ]

    commission_type = models.CharField(max_length=20, choices=COMMISSION_TYPE_CHOICES)
    policy_id = models.IntegerField()
    policy_number = models.CharField(max_length=100)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name='fk_uploaded_log_by', null= True,blank=True)
    updated_from = models.CharField(max_length=100) 
    updated_data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    upload_id = models.BigIntegerField(null=True)
    status = models.IntegerField(default=0)
    

    def __str__(self):
        return f"{self.commission_type} - {self.policy_number} - {self.updated_by_id}"

    class Meta:
        db_table = 'commission_update_log'