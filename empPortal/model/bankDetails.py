from django.db import models

class BankDetails(models.Model):
    user_id = models.CharField(max_length=20, null=True, blank=True)
    account_holder_name = models.CharField(max_length=255)
    account_number = models.CharField(max_length=50, unique=True)
    re_enter_account_number = models.CharField(max_length=50)
    ifsc_code = models.CharField(max_length=20)
    bank_name = models.CharField(max_length=255)
    branch_name = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'bank_details'

    def __str__(self):
        return f"{self.account_holder_name} - {self.bank_name} ({self.account_number})"
