from django.db import models

class VehicleType(models.Model):
    name = models.CharField(max_length=255, null=True, blank=True)
    status = models.IntegerField(default=1)  # 1 for active, 0 for inactive
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name}"

    class Meta:
        db_table = 'vehicle_types'
