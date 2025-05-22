from django.db import models

class WimMasterInsurer(models.Model):
    master_insurer_name = models.CharField(max_length=75, null=True, blank=True)
    master_insurer_address = models.TextField(null=True, blank=True)
    master_insurer_is_active = models.BooleanField(default=True)  # 1 = Active, 0 = Inactive
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'wim_master_insurers'
        verbose_name = 'Master Insurer'
        verbose_name_plural = 'Master Insurers'

    def __str__(self):
        return self.master_insurer_name or f"Insurer {self.id}"
