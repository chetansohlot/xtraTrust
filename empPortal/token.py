import jwt
from datetime import datetime, timedelta
from django.conf import settings

SECRET_KEY = settings.APP_SECRET_KEY

def generate_employee_token(employee_id):
    payload = {
        'employee_id': employee_id,
        'exp': datetime.utcnow() + timedelta(days=1),  # token expires in 1 day
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')
