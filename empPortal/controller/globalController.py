from django.shortcuts import redirect
from django.urls import reverse

def global_search(request):
    category = request.GET.get('category', '').strip()
    query = request.GET.get('global_search', '').strip()

    if category == 'agents':
        return redirect(f"{reverse('members')}?global_search={query}")
    elif category == 'lead':
        return redirect(f"{reverse('leads-mgt')}?global_search={query}")

    return redirect('dashboard') 