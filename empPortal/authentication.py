from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model
from django.http import HttpResponse

User = get_user_model()

class EmailAuthBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        user = User.objects.filter(email=username).first()
        if user and user.check_password(password):
            return user
        return None

    def get_user(self, user_id):
        return User.objects.filter(pk=user_id).first()
