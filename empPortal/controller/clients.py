from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from empPortal.model import Credential
from django.contrib import messages



def index(request):
    if not request.user.is_authenticated and request.user.is_active != 1:
        messages.error(request,'Please Login First')
        return redirect('login')
    return render(request,'clients/index.html')