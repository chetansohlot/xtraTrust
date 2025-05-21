from django.db import models

class EmployeeDetails(models.Model):
    # Primary Key
    employee_id = models.AutoField(primary_key=True)

    # Basic Details
    user_id = models.IntegerField()  # No foreign key, just an integer field
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=6, choices=[('Male', 'Male'), ('Female', 'Female')])
    pan_card = models.CharField(max_length=20)
    aadhar_card = models.CharField(max_length=20)
    mobile_number = models.CharField(max_length=15)
    email_address = models.EmailField(max_length=100)
    blood_group = models.CharField(max_length=10)
    marital_status = models.CharField(max_length=20)

    # Permanent Address
    permanent_address = models.TextField()
    permanent_state = models.CharField(max_length=100)
    permanent_city = models.CharField(max_length=100)
    permanent_pincode = models.CharField(max_length=10)

    # Correspondence Address
    correspondence_address = models.TextField()
    correspondence_state = models.CharField(max_length=100)
    correspondence_city = models.CharField(max_length=100)
    correspondence_pincode = models.CharField(max_length=10)

    # Family Details - Father
    father_first_name = models.CharField(max_length=100)
    father_last_name = models.CharField(max_length=100)
    father_dob = models.DateField()

    # Family Details - Mother
    mother_first_name = models.CharField(max_length=100)
    mother_last_name = models.CharField(max_length=100)
    mother_dob = models.DateField()

    # Employment Info
    employee_code = models.CharField(max_length=50, null=True, blank=True)
    department = models.CharField(max_length=100, null=True, blank=True)
    date_of_joining = models.DateField(null=True, blank=True)

    # References (Optional)
    reference1_relation_type = models.CharField(max_length=100, null=True, blank=True)
    reference1_first_name = models.CharField(max_length=100, null=True, blank=True)
    reference1_last_name = models.CharField(max_length=100, null=True, blank=True)
    reference1_mobile_number = models.CharField(max_length=15, null=True, blank=True)
    reference1_email_address = models.EmailField(max_length=100, null=True, blank=True)

    reference2_relation_type = models.CharField(max_length=100, null=True, blank=True)
    reference2_first_name = models.CharField(max_length=100, null=True, blank=True)
    reference2_last_name = models.CharField(max_length=100, null=True, blank=True)
    reference2_mobile_number = models.CharField(max_length=15, null=True, blank=True)
    reference2_email_address = models.EmailField(max_length=100, null=True, blank=True)

    # Audit Fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    active = models.BooleanField(default=True)

    class Meta:
        db_table = 'employee_details'
    def __str__(self):
        return f"{self.first_name} {self.last_name}"
