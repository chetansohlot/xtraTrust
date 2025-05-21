from django.db import models


class Referral(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    address = models.TextField(blank=True, null=True)
    mobile = models.CharField(max_length=15, unique=True, blank=True, null=True)
    referral_code = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    active = models.BooleanField(default=True)

    dob = models.DateField(null=True, blank=True)
    date_of_anniversary = models.DateField(null=True, blank=True)
    pan_card_number = models.CharField(max_length=10, null=True, blank=True)
    aadhar_no = models.CharField(max_length=15,null=True, blank=True)

    user_role = models.CharField(max_length=100, null=True, blank=True)
    bqp_id = models.IntegerField(null=True)
    branch = models.CharField(max_length=100, null=True, blank=True)
    sales = models.CharField(max_length=100, null=True, blank=True)
    supervisor = models.CharField(max_length=100, null=True, blank=True)
    franchise = models.CharField(max_length=100, null=True, blank=True)
    pincode = models.CharField(max_length=10, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    state = models.CharField(max_length=100, null=True, blank=True)

    referral_is_delete = models.BooleanField(default=False)
    referral_deleted_by = models.ForeignKey('Users', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.name} - {self.referral_code}"

    class Meta:
        db_table = 'referrals'  # 👈 This tells Django to use your existing table

class Ref_Bank_Details(models.Model):
    referral = models.OneToOneField(Referral, on_delete=models.CASCADE, related_name='bank_details')
    bank_category = models.CharField(max_length=100)
    bank_name = models.CharField(max_length=100)
    account_type = models.CharField(max_length=50)
    ifsc_code = models.CharField(max_length=20)
    branch_name = models.CharField(max_length=100)
    account_holder_name = models.CharField(max_length=100)
    account_number = models.CharField(max_length=30)

    

    def __str__(self):
        return f"{self.referral.name}'s Bank Details"
    
    class Meta:
        db_table ='ref_bank_deatils'