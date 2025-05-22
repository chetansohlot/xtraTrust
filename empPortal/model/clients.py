from django.db import models

class XtClientsBasicInfo(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]
     
    client_name = models.CharField(max_length=255)
    company_type = models.CharField(max_length=100, blank=True, null=True)
    pan_number = models.CharField(max_length=20, blank=True, null=True)
    gst_number = models.CharField(max_length=20, blank=True, null=True)
    cin_number = models.CharField(max_length=25, blank=True, null=True)
    official_email = models.EmailField(max_length=255, blank=True, null=True)
    mobile = models.CharField(max_length=20, blank=True, null=True)
    landline = models.CharField(max_length=20, blank=True, null=True)
    country = models.CharField(max_length=100, default='India')
    state = models.CharField(max_length=100, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    active = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='active'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'xt_clients_basic_info'

    def __str__(self):
        return self.client_name or "Unnamed Client"
    
class XtClientsContactInfo(models.Model):
    client = models.ForeignKey(
        'XtClientsBasicInfo',
        on_delete=models.CASCADE,
        related_name='contact_info'
    )

    primary_first_name = models.CharField(max_length=100, blank=True, null=True)
    primary_last_name = models.CharField(max_length=100, blank=True, null=True)
    primary_designation = models.CharField(max_length=100, blank=True, null=True)
    primary_mobile = models.CharField(max_length=20, blank=True, null=True)
    primary_email = models.EmailField(max_length=255, blank=True, null=True)
    primary_landline = models.CharField(max_length=20, blank=True, null=True)

    secondary_first_name = models.CharField(max_length=100, blank=True, null=True)
    secondary_last_name = models.CharField(max_length=100, blank=True, null=True)
    secondary_designation = models.CharField(max_length=100, blank=True, null=True)
    secondary_mobile = models.CharField(max_length=20, blank=True, null=True)
    secondary_email = models.EmailField(max_length=255, blank=True, null=True)
    secondary_landline = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        db_table = 'xt_clients_contact_info'

    def __str__(self):
        return f"Contacts for {self.client.client_name}" if self.client and self.client.client_name else "Contacts for Unnamed Client"
