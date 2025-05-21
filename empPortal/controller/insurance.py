from django.shortcuts import render, redirect
from django.contrib import messages

from empPortal.model.StateCity import City, State
from ..model import Insurance
from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from django.core.validators import validate_email
from django.core.exceptions import ValidationError

def insurance_list(request):
    if not request.user.is_authenticated and request.user.is_active!=1:
        messages.error(request,'Please Login First')
        return redirect('login')

    insurance_qs = Insurance.objects.all().order_by('-created_at')


    # Pagination
    page_number = request.GET.get('page', 1)
    per_page = request.GET.get('per_page', 10)
    search_field = request.GET.get('search_field', '')  # Field to search
    search_query = request.GET.get('search_query', '') 

    try:
        per_page = int(per_page)
    except ValueError:
        per_page = 10  # Default to 10 if invalid value is given

    # Apply filtering
    # if search_field and search_query:
    #     if search_field in [f.name for f in Insurance._meta.get_fields()]:
    #         filter_args = {f"{search_field}__icontains": search_query}
    #         insurance_qs = insurance_qs.filter(**filter_args)
    #     else:
    #         messages.warning(request, f"Invalid search field: {search_field}")

    if search_field and search_query:
            filter_args = {f"{search_field}__icontains": search_query}
            insurance_qs = insurance_qs.filter(**filter_args)        
    
   # Paginate results
    paginator = Paginator(insurance_qs, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    total_count = insurance_qs.count()
    active_count = insurance_qs.filter(active='Active').count()    # updated value
    inactive_count = insurance_qs.filter(active='Inactive').count()  # updated value
    return render(request, 'insurance/insurance_index.html',
                  {
                      'page_obj': page_obj,
                      'total_count': total_count,
                      'active_count': active_count,
                      'inactive_count': inactive_count,
                      'per_page': per_page,
                      'search_field': search_field,
                      'search_query': search_query,
                  })

def insurance_create(request):
    if not request.user.is_authenticated and request.user.is_active!=1:
        messages.error(request,'Please Login First')
        return redirect('login')

    states = State.objects.all()
    cities = City.objects.all()

    if request.method == 'POST':
        name = request.POST.get('insurance_company')
        ins_short_name =request.POST.get('ins_short_name')
        status = request.POST.get('active', 'Active')

        # Registered Address (match template field names)
        state_id = request.POST.get('registered_state')
        city_id = request.POST.get('registered_city')
        pincode = request.POST.get('registered_pincode')
        address = request.POST.get('registered_address')

        # Billing Address
        billing_same_as_registered = request.POST.get('billing_same_as_registered')
        billing_state_id = request.POST.get('billing_state')
        billing_city_id = request.POST.get('billing_city')
        billing_pincode = request.POST.get('billing_pincode')
        billing_address = request.POST.get('billing_address')
        commencement_date = request.POST.get('commencement_date')


        billing_same_as_registered = True if billing_same_as_registered == 'on' else False

        # Backend Validation
        """errors = []

        if not name:
            errors.append("Insurance company name is required.")

        if not state_id:
            errors.append("Registered state is required.")

        if not city_id:
            errors.append("Registered city is required.")

        if not pincode:
            errors.append("Registered pincode is required.")

        if not address:
            errors.append("Registered address is required.")

        if not billing_same_as_registered:
            if not billing_state_id:
                errors.append("Billing state is required.")
            if not billing_city_id:
                errors.append("Billing city is required.")
            if not billing_pincode:
                errors.append("Billing pincode is required.")
            if not billing_address:
                errors.append("Billing address is required.")

        # If errors, show messages and return to form
        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, 'insurance/insurance-create.html', {'states': states, 'cities': cities, })"""


        # Get ForeignKey instances
        state = State.objects.filter(id=state_id).first() if state_id else None
        city = City.objects.filter(id=city_id).first() if city_id else None
        billing_state=State.objects.filter(id=billing_state_id).first() if billing_state_id else None
        billing_city=City.objects.filter(id=billing_city_id).first() if billing_city_id else None

        insurance = Insurance.objects.create(
            insurance_company=name,
            ins_short_name=ins_short_name,
            active=status,
            pincode=pincode if pincode else None,
            address=address,
            state=state,
            city=city,
            billing_state=billing_state,
            billing_city=billing_city,
            billing_pincode=billing_pincode if billing_pincode else None,
            billing_address=billing_address,
            commencement_date=commencement_date if commencement_date else None,
            billing_same_as_registered=billing_same_as_registered,
        )

        messages.success(request, 'Insurance Type created successfully.')
        return redirect('create-contact-detail', id=insurance.id)

    return render(request, 'insurance/insurance-create.html', {'states': states, 'cities': cities})

def insurance_contact_details(request, id):
    if not request.user.is_authenticated or not request.user.is_active:
        messages.error(request, 'Please login first.')
        return redirect('login')

    insurance = Insurance.objects.filter(id=id).first()
    if not insurance:
        messages.error(request, "Invalid Insurance ID.")
        return redirect('insurance-create')

    if request.method == "POST":
        primary_name = request.POST.get('primary_name')
        primary_designation = request.POST.get('primary_designation')
        primary_contact = request.POST.get('primary_contact')
        primary_email = request.POST.get('primary_email')

        secondary_name = request.POST.get('secondary_name')
        secondary_designation = request.POST.get('secondary_designation')
        secondary_contact = request.POST.get('secondary_contact')
        secondary_email = request.POST.get('secondary_email')

        has_error = False

        # Validate Primary Contact Details
        if not primary_name:
            messages.error(request, 'Primary contact name is required.')
            has_error = True

        if not primary_designation:
            messages.error(request, 'Primary contact designation is required.')
            has_error = True

        if not primary_contact:
            messages.error(request, 'Primary contact number is required.')
            has_error = True
        elif not primary_contact.isdigit() or len(primary_contact) != 10:
            messages.error(request, 'Primary contact number must be a valid 10-digit number.')
            has_error = True

        if not primary_email:
            messages.error(request, 'Primary email is required.')
            has_error = True
        else:
            try:
                validate_email(primary_email)
            except ValidationError:
                messages.error(request, 'Primary email is invalid.')
                has_error = True

        # Validate Secondary Contact if provided
        if secondary_contact:
            if not secondary_contact.isdigit() or len(secondary_contact) != 10:
                messages.error(request, 'Secondary contact number must be a valid 10-digit number.')
                has_error = True

        if secondary_email:
            try:
                validate_email(secondary_email)
            except ValidationError:
                messages.error(request, 'Secondary email is invalid.')
                has_error = True

        if not has_error:
            insurance.primary_contact_name = primary_name
            insurance.primary_designation = primary_designation
            insurance.primary_contact_no = primary_contact
            insurance.primary_contact_email = primary_email
            insurance.secondary_contact_name = secondary_name
            insurance.secondary_designation = secondary_designation
            insurance.secondary_contact_no = secondary_contact
            insurance.secondary_contact_email = secondary_email
            insurance.created_by = request.user
            insurance.save()

            messages.success(request, "Insurance contact details saved successfully.")
            return redirect('insurance_index')
        else:
            return redirect('create-contact-detail',id=id)
    
    else:
        return render(request, "insurance/create-contact-detail.html", {'insurance_id': id})


def insurance_edit(request, insurance_id):
    if not request.user.is_authenticated and request.user.is_active!=1:
        messages.error(request,'Please Login First')
        return redirect('login')

    insurance = get_object_or_404(Insurance, id=insurance_id)
    states = State.objects.all()
    cities = City.objects.all()

    if request.method == 'POST':
        insurance.insurance_company = request.POST.get('insurance_company')
        insurance.ins_short_name =request.POST.get('ins_short_name')
        insurance.active = request.POST.get('active', 'Active')

        # Registered Address
        state_id = request.POST.get('registered_state')
        city_id = request.POST.get('registered_city')
        pincode = request.POST.get('registered_pincode')
        address = request.POST.get('registered_address')

        state = State.objects.filter(id=state_id).first() if state_id else None
        city = City.objects.filter(id=city_id).first() if city_id else None

        #insurance.state = state
        #insurance.city = city
        insurance.state = state.name if state else None
        insurance.city = city.city if city else None
        insurance.pincode = pincode if pincode else None
        insurance.address = address

        # Billing Address
        billing_state_id = request.POST.get('billing_state')
        billing_city_id = request.POST.get('billing_city')
        billing_pincode = request.POST.get('billing_pincode')
        billing_address = request.POST.get('billing_address')
        commencement_date = request.POST.get('commencement_date')

        billing_state = State.objects.filter(id=billing_state_id).first() if billing_state_id else None
        billing_city = City.objects.filter(id=billing_city_id).first() if billing_city_id else None

        #insurance.billing_state = billing_state
        #insurance.billing_city = billing_city
        insurance.billing_state = billing_state.name if billing_state else None
        insurance.billing_city = billing_city.city if billing_city else None
        insurance.billing_pincode = billing_pincode
        insurance.billing_address = billing_address
        insurance.commencement_date = commencement_date

        insurance.save()
        messages.success(request, 'Insurance updated successfully.')
        return redirect('insurance_index')

    return render(request, 'insurance/insurance-create.html', {
        'insurance': insurance,
        'states': states,
        'cities': cities
    })


def toggle_insurance_status(request, insurance_id):
    if not request.user.is_authenticated and request.user.is_active!=1:
        messages.error(request,'Please Login First')
        return redirect('login')

    insurance = get_object_or_404(Insurance, id=insurance_id)

    if insurance.active == 'Active':
        insurance.active = 'Inactive'
        messages.info(request, 'Insurance deactivated successfully.')
    else:
        insurance.active = 'Active'
        messages.success(request, 'Insurance activated successfully.')

    insurance.save()
    return redirect('insurance_index')

def get_state(request):
    states = State.objects.all()
    return render(request, 'insurance/insurance-create.html', {'states': states})

def get_cities(request):
    state_id = request.GET.get('state_id')
    cities = City.objects.filter(state_id=state_id).values('id', 'city')
    return JsonResponse({'cities': list(cities)})
