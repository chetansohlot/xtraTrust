from django.db import models

class Employees(models.Model):
    employee_id = models.AutoField(primary_key=True)
    user_id = models.IntegerField()
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=20)
    pan_card = models.CharField(max_length=20)
    aadhaar_card = models.CharField(max_length=20)
    mobile_number = models.CharField(max_length=15)
    email_address = models.EmailField(max_length=150)
    blood_group = models.CharField(max_length=5)
    marital_status = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    active = models.BooleanField(default=True)

    class Meta:
        db_table = 'employees' 

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def id(self):
        return self.employee_id

    def get_user(self):
        from ..models import Users  

        """Returns the related Users object if it exists, else None."""
        try:
            return Users.objects.get(id=self.user_id)
        except Users.DoesNotExist:
            return None
        
    def get_address(self):
        """Returns the related Users object if it exists, else None."""
        try:
            return Address.objects.get(employee_id=self.employee_id)
        except Address.DoesNotExist:
            return None
        
    def get_family(self):
        """Returns the related Users object if it exists, else None."""
        try:
            return FamilyDetail.objects.get(employee_id=self.employee_id)
        except FamilyDetail.DoesNotExist:
            return None
        
    def get_emp_info(self):
        """Returns the related Users object if it exists, else None."""
        try:
            return EmploymentInfo.objects.get(employee_id=self.employee_id)
        except EmploymentInfo.DoesNotExist:
            return None
        
    def get_emp_ref(self):
        """Returns the related Users object if it exists, else None."""
        try:
            return EmployeeReference.objects.get(employee_id=self.employee_id)
        except EmployeeReference.DoesNotExist:
            return None
        
    @property
    def is_authenticated(self):
        return True

class Address(models.Model):
    address_id = models.AutoField(primary_key=True)
    employee_id = models.IntegerField()  # Assuming this is a simple foreign key to Employees table
    type = models.CharField(max_length=30)  # 'type' as VARCHAR(30)
    address = models.TextField()
    state = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    active = models.BooleanField(default=True)

    class Meta:
        db_table = 'employee_addresses'  # Using the default table name 'addresses'

    def get_state(self):
        from empPortal.model.StateCity import State
        """Returns the related Users object if it exists, else None."""
        try:
            return State.objects.get(id=self.state)
        except State.DoesNotExist:
            return None
        
    def get_city(self):
        from empPortal.model.StateCity import City
        """Returns the related Users object if it exists, else None."""
        try:
            return City.objects.get(id=self.city)
        except City.DoesNotExist:
            return None
        
    def __str__(self):
        return f"Address for Employee ID {self.employee_id} ({self.type})"
    


class FamilyDetail(models.Model):
    family_id = models.AutoField(primary_key=True)
    employee_id = models.IntegerField()  # Assuming this is a simple foreign key to Employees table
    relation = models.CharField(max_length=30)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    date_of_anniversary = models.DateField(null=True, blank=True)  # Optional field for anniversary
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    active = models.BooleanField(default=True)

    class Meta:
        db_table = 'family_details'  # Using the default table name 'family_details'

    def __str__(self):
        return f"Family Member: {self.first_name} {self.last_name} ({self.relation})"


class EmploymentInfo(models.Model):
    emp_info_id = models.AutoField(primary_key=True)
    employee_id = models.IntegerField()  # Assuming this is a simple foreign key to Employees table
    employee_code = models.CharField(max_length=50)
    designation = models.CharField(max_length=100)
    date_of_joining = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    active = models.BooleanField(default=True)

    class Meta:
        db_table = 'employment_info'  # Using the default table name 'employment_info'

    def __str__(self):
        return f"Employment Info for Employee ID {self.employee_id} ({self.designation})"




class EmployeeReference(models.Model):
    reference_id = models.AutoField(primary_key=True)
    employee_id = models.IntegerField()  # Assuming this is a simple foreign key to Employees table
    relation = models.CharField(max_length=50)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    mobile_number = models.CharField(max_length=15)
    email_address = models.EmailField(max_length=150)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    active = models.BooleanField(default=True)

    class Meta:
        db_table = 'employee_references'  # Using the default table name 'employee_references'

    def __str__(self):
        return f"Reference for Employee ID {self.employee_id} ({self.relation})"
