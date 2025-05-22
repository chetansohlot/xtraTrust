from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from ..authentication import EmployeeAuthentication
from ..token import generate_employee_token
from empPortal.model import Employees
from empPortal.serializers import EmployeeSerializer


@api_view(['POST'])
def employee_login(request):
    email = request.data.get('email')

    try:
        employee = Employees.objects.get(email_address=email,active=True)
        token = generate_employee_token(employee.employee_id)
        return Response({'token': token})
    except Employees.DoesNotExist:
        return Response({'error': 'Invalid Credentials'}, status=400)
    
@api_view(['GET'])
@authentication_classes([EmployeeAuthentication])
def get_employee_data(request):
    employee = request.user
    serialized = EmployeeSerializer(employee)
    return Response(serialized.data)