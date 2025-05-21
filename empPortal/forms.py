from django import forms
from .models import DocumentUpload, SourceMaster

class DocumentUploadForm(forms.ModelForm):
    class Meta:
        model = DocumentUpload
        fields = "__all__"

##  Source Master ---> Source ##

# from django import forms
# from .models import SourceMaster

# class SourceMasterForm(forms.ModelForm):
#     class Meta:
#         model = SourceMaster
#         fields = ['source_name', 'sort_source_name', 'status']


