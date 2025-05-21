from django.db import models

class vehicleDetails(models.Model):
    registration_number = models.CharField(max_length=20, null=True, blank=True)
    vehicle_details = models.TextField(null=True, blank=True)
    active = models.BooleanField(default=True)  # Default to active (1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "vehicle_details"

    def __str__(self):
        return f"Vehicle {self.registration_number or 'N/A'}"
    