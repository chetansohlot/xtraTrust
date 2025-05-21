from django.shortcuts import render,redirect,get_object_or_404
from ..models import BqpMaster

def bqp_list(request):
    bqp_qs = BqpMaster.objects.all().order_by('-created_at')


    total_count =bqp_qs.count()
    active_count =bqp_qs.filter(bqp_status=True).count()
    inactive_count =bqp_qs.filter(bqp_status=False).count()

    return render(request, 'bqp/bqp_index.html',
                   {'bqp_qs': bqp_qs,
                    'total_count':total_count,
                    'active_count':active_count,
                    'inactive_count':inactive_count,
                    }
                )

def bqp_create(request):
    if request.method == 'POST':
        pan_number =request.POST.get('pan_number')
        fname =request.POST.get('bqp_fname')
        lname =request.POST.get('bqp_lname')
        email_address =request.POST.get('email_address')
        mobile_number =request.POST.get('mobile_number')

        bqp_status = True

        ## Save DB ##
        BqpMaster.objects.create(
            bqp_fname=fname,
            bqp_lname=lname,
            pan_number=pan_number,
            email_address=email_address,
            mobile_number=mobile_number,
            bqp_status = bqp_status
        )
        return redirect('bqp_list')
    
    return render(request, 'bqp/bqp_create.html')

def bqp_edit(request,bqp_id):
    bqp =get_object_or_404(BqpMaster,id=bqp_id)
    if request.method =='POST':
        bqp.pan_number =request.POST.get('pan_number')
        bqp.bqp_fname =request.POST.get('bqp_fname')
        bqp.bqp_lname =request.POST.get('bqp_lname')
        bqp.email_address =request.POST.get('email_address')
        bqp.mobile_number =request.POST.get('mobile_number')
        bqp.save()
        return redirect('bqp_list')  

    return render(request, 'bqp/bqp_create.html', {'bqp': bqp})


def bqp_delete(request,bqp_id):
    source = get_object_or_404(BqpMaster,id=bqp_id)
    source.delete()
    return redirect('bqp_list')


