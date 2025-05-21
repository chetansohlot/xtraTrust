from django.shortcuts import render, redirect, get_object_or_404
from ..models import SourceMaster 


def source_list(request):
    sources = SourceMaster.objects.all().order_by('-created_at')

    total_count =sources.count()
    active_count =sources.filter(status=True).count()
    inactive_count =sources.filter(status=False).count()

    return render(request, 'source/index.html',
                   {'sources': sources,
                    'total_count':total_count,
                    'active_count':active_count,
                    'inactive_count':inactive_count,
                    }
                )

# Create Source
def source_create(request):
    if request.method == 'POST':
        source_name = request.POST.get('source_name')
        sort_source_name = request.POST.get('sort_source_name')

        # Create the new source
        SourceMaster.objects.create(
            source_name=source_name,
            sort_source_name=sort_source_name
        )
        return redirect('source_list')  

    return render(request, 'source/create.html')

# Edit Source
def source_edit(request, source_id):
    source = get_object_or_404(SourceMaster, id=source_id)
    if request.method == 'POST':
        source.source_name = request.POST.get('source_name')
        source.sort_source_name = request.POST.get('sort_source_name')
        source.save()
        return redirect('source_list')  

    return render(request, 'source/create.html', {'source': source})

def source_delete(request,source_id):
    source = get_object_or_404(SourceMaster,id=source_id)
    source.delete()
    return redirect('source_list')


