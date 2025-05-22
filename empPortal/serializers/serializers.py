from rest_framework import serializers
from empPortal.model import Employees
class EmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employees
        fields = ['employee_id', 'email_address']