
from django.db import models   
class Quotation(models.Model):
    customer_id = models.CharField(max_length=25, null=True, blank=True)
    created_by = models.CharField(max_length=100)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'quotations'  # Explicit table name if it already exists in the DB

    def __str__(self):
        return f"Quotation #{self.id} - Customer: {self.customer_id}"