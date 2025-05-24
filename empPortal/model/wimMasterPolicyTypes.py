from django.db import models

class MasterPolicyType(models.Model):
    master_policy_type_name = models.CharField(max_length=75, null=True, blank=True)
    master_policy_type_description = models.TextField(null=True, blank=True)
    master_policy_type_is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'wim_master_policy_types'

    def __str__(self):
        return self.master_policy_type_name or f"Policy Type {self.id}"
