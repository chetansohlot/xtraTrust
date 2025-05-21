from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from empPortal.model import Credential
from django.contrib import messages

def credential_list(request):
    credentials =Credential.objects.all()

    # Count summary
    total_count = credentials.count()
    active_count = credentials.filter(credential_status=True).count()
    inactive_count = credentials.filter(credential_status=False).count()

    context = {
        'credentials': credentials,
        'total_count': total_count,
        'active_count': active_count,
        'inactive_count': inactive_count,
    }
    return render(request, 'credential-mgt/credential_index.html', context)


def credential_create(request):
    if request.method == 'POST':
        credential_platform_name= request.POST.get('credential_platform_name')
        credential_url= request.POST.get('credential_url')
        credential_username= request.POST.get('credential_username')
        credential_password= request.POST.get('credential_password')
        credential_remark = request.POST.get('credential_remark')

        credential_status= True
        
        Credential.objects.create(
            credential_platform_name=credential_platform_name,
            credential_url=credential_url,
            credential_username=credential_username,
            credential_password=credential_password,
            credential_remark=credential_remark,
            credential_status=credential_status
        )
        messages.success(request, "Credential created sucessfully.")
        return redirect('credential_list')
    
    return render(request, 'credential-mgt/credential_create.html')

def credential_edit(request,credential_id):
    credential =get_object_or_404(Credential,id=credential_id)
    if request.method == 'POST':
        credential.credential_platform_name= request.POST.get('credential_platform_name')
        credential.credential_url= request.POST.get('credential_url')
        credential.credential_username= request.POST.get('credential_username')
        credential.credential_password= request.POST.get('credential_password')
        credential.credential_remark = request.POST.get('credential_remark')
        credential.save()
        messages.success(request, "Credential updated sucessfully.")
        return redirect('credential_list')
    
    return render(request, 'credential-mgt/credential_create.html', {'credential' : credential})

# def credential_delete(request,credential_id):
#     credential =get_object_or_404(Credential,id=credential_id)
#     # credential.credential_status= not credential.credential_status
#     if credential.credential_status is True:
#         credential.credential_status = False
#     else : 
#         credential.credential_status = True 

#     credential.save()
#     return redirect('credential_list')

def credential_delete(request, credential_id):
    try:
        credential = get_object_or_404(Credential, id=credential_id)

        # Toggle status instead of deleting
        credential.credential_status = not credential.credential_status
        credential.save()

        return JsonResponse({'success': True, 'new_status': credential.credential_status})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})