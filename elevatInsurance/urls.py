from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponseNotFound
from django.shortcuts import render

def custom_404_view(request, exception=None):
    return render(request, '404.html', status=404)

urlpatterns = [
    path('', include('empPortal.urls')),
    path('admin/', admin.site.urls),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

handler404 = 'elevatInsurance.urls.custom_404_view'
