from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model
from django.http import HttpResponse

import jwt
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from empPortal.model import Employees


User = get_user_model()

class EmailAuthBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        user = User.objects.filter(email=username).first()
        if user and user.check_password(password):
            return user
        return None

    def get_user(self, user_id):
        return User.objects.filter(pk=user_id).first()

class EmployeeAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get('Authorization')

        if not auth_header or not auth_header.startswith('Bearer '):
            return None

        token = auth_header.split(' ')[1]

        try:
            payload = jwt.decode(token, settings.APP_SECRET_KEY, algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed('Token expired')
        except jwt.InvalidTokenError:
            raise AuthenticationFailed('Invalid token')

        try:
            employee = Employees.objects.get(employee_id=payload['employee_id'])
        except Employees.DoesNotExist:
            raise AuthenticationFailed('Employee not found')

        return (employee, token)