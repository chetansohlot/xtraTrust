from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from empPortal.model import XtClientsBasicInfo, XtClientsContactInfo
from django.contrib import messages



def index(request):
    if not request.user.is_authenticated and request.user.is_active != 1:
        messages.error(request,'Please Login First')
        return redirect('login')
    

    # clients_info =XtClientsBasicInfo.objects.filter(active=True).order_by('-id')
    clients_info = XtClientsBasicInfo.objects.filter().order_by('-id').prefetch_related('contact_info')


    paginator = Paginator(clients_info, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)


    # client_contact_info = XtClientsContactInfo.objects.filter(client__in=clients_info)
    return render(request,'clients/index.html',{
            'clients_info':page_obj,
            # 'client_contact_info':client_contact_info,
    })


def clean(val):
    return val.strip() if isinstance(val, str) and val.strip() else None

def client_basic_info(request,id=None):
    if not request.user.is_authenticated and request.user.is_active!=1:
        messages.error(request,'Please Login First')
        return redirect('login')
    
    if id:
        client = get_object_or_404(XtClientsBasicInfo, id=id)
    else:
        client = None  # For creating new client

    return render(request, 'clients/create-basic-info.html', {'client': client})

def save_clients_basic_info(request):
    if not request.user.is_authenticated or not request.user.is_active:
        messages.error(request, 'Please login first')
        return redirect('login')

    if request.method != 'POST':
        messages.error(request, 'Invalid request method')
        return redirect('client-view')

    client_id = request.POST.get('client_id') or None
    
    try:
        if client_id:
            client = XtClientsBasicInfo.objects.filter(id=client_id).first()
            if not client:
                messages.error(request, 'Client not found')
                return redirect('client-view')
        else:
            client = XtClientsBasicInfo()

        # Assign values ka hai (clean inputs as needed)
        client.client_name = clean(request.POST.get('client_name', ''))
        client.company_type = clean(request.POST.get('company_type', ''))
        client.pan_number = clean(request.POST.get('pan_number', ''))
        client.gst_number = clean(request.POST.get('gst_number', ''))
        client.cin_number = clean(request.POST.get('cin_number', ''))
        client.official_email = clean(request.POST.get('official_email', ''))
        client.mobile = clean(request.POST.get('mobile', ''))
        client.landline = clean(request.POST.get('landline', ''))
        client.country = clean(request.POST.get('country', ''))
        client.state = clean(request.POST.get('state', ''))
        client.city = clean(request.POST.get('city', ''))
        client.address = clean(request.POST.get('address', ''))
        client.save()


        client_id=client.id

        messages.success(request, f"Client info {'updated' if client_id else 'saved'} successfully.")
        return redirect('create-contact-info', id=client_id)

    except Exception as e:
        messages.error(request, 'Something went wrong. Please try again.')
        return redirect('client-view')

def client_contact_info(request, id=None):
    if not request.user.is_authenticated or not request.user.is_active:
        messages.error(request, 'Please login first')
        return redirect('login')

    client = get_object_or_404(XtClientsBasicInfo, id=id) if id else None
    contact_info = XtClientsContactInfo.objects.filter(client=client).first() if client else None

    return render(request, 'clients/create-contact-info.html', {
        'client': client,
        'contact_info': contact_info
    })
     
def save_contacts_info(request):
    if not request.user.is_authenticated or not request.user.is_active:
        messages.error(request, 'Please login first')
        return redirect('login')

    if request.method != 'POST':
        messages.error(request, 'Invalid request method')
        return redirect('client-view')

    client_id = request.POST.get('client_id')
    print("Clients ID Received:" ,client_id)

    if not client_id:
        messages.error(request, 'Client ID missing')
        return redirect('client-view')

    client = XtClientsBasicInfo.objects.filter(id=client_id).first()
    if not client:
        messages.error(request, 'Client not found')
        return redirect('client-view')

    try:
        contact_info, _ = XtClientsContactInfo.objects.get_or_create(client=client)

        contact_info.primary_first_name = clean(request.POST.get('primary_first_name'))
        contact_info.primary_last_name = clean(request.POST.get('primary_last_name'))
        contact_info.primary_designation = clean(request.POST.get('primary_designation'))
        contact_info.primary_mobile = clean(request.POST.get('primary_mobile'))
        contact_info.primary_email = clean(request.POST.get('primary_email'))
        contact_info.primary_landline = clean(request.POST.get('primary_landline'))

        contact_info.secondary_first_name = clean(request.POST.get('secondary_first_name'))
        contact_info.secondary_last_name = clean(request.POST.get('secondary_last_name'))
        contact_info.secondary_designation = clean(request.POST.get('secondary_designation'))
        contact_info.secondary_mobile = clean(request.POST.get('secondary_mobile'))
        contact_info.secondary_email = clean(request.POST.get('secondary_email'))
        contact_info.secondary_landline = clean(request.POST.get('secondary_landline'))

        contact_info.save()

        messages.success(request, 'Contact info saved successfully.')
        return redirect('client-view')

    except Exception as e:
        messages.error(request, f'Something went wrong while saving contact info: {str(e)}')
        return redirect('client-view')
    
def clients_delete(request,id):
    try:
        clients = get_object_or_404(XtClientsBasicInfo, id=id)

        # Toggle status instead of deleting
        clients.active = not clients.active
        clients.save()

        return JsonResponse({'success': True, 'new_status': clients.active})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
