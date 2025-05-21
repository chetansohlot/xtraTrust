from django.db import models

class Credential(models.Model):
    credential_platform_name=models.CharField(max_length=255, null=True, blank=True)
    credential_url =models.URLField(null=True, blank=True)
    credential_username =models.CharField(max_length=255,null=True, blank=True)
    credential_password =models.CharField(max_length=255,null=True, blank=True)
    credential_remark =models.CharField(max_length=255,null=True, blank=True)
    credential_status = models.BooleanField(null=True, default=True)  
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta :
        db_table ="credential_mgt"

    def __str__(self):
        return self.credential_platform_name
        
