# middleware.py

from django.shortcuts import redirect
from django.utils import timezone

class AutoLogoutMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            last_activity = request.session.get('last_activity')
            now = timezone.now().timestamp()
            timeout = 3600  #1 Hour

            # if last_activity and (now - last_activity > timeout):
            #     from django.contrib.auth import logout
            #     logout(request)
            #     return redirect('login')

            # request.session['last_activity'] = now

        return self.get_response(request)
