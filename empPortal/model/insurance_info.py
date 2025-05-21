from django.db import models
class InsuranceType(models.Model):
    id = models.AutoField(primary_key=True, db_column='insurance_type_id')
    name = models.CharField(max_length=100, db_column='insurance_type_name')
    created_at = models.DateTimeField(auto_now_add=True, db_column='insurance_type_created_at')
    updated_at = models.DateTimeField(auto_now=True, db_column='insurance_type_updated_at')
    status = models.CharField(max_length=10, default='Active', db_column='insurance_type_status')
    
    class Meta:
        db_table = 'ni_insurance_type'
        verbose_name = 'Insurance Type'
        verbose_name_plural = 'Insurance Types'

    def __str__(self):
        return self.name


class InsuranceCategory(models.Model):
    id = models.AutoField(primary_key=True, db_column='category_id')
    name = models.CharField(max_length=100, db_column='insurance_category_name')
    insurance_type = models.ForeignKey(
        InsuranceType,
        on_delete=models.CASCADE,
        db_column='insurance_type_id',
        related_name='categories'
    )
    created_at = models.DateTimeField(auto_now_add=True, db_column='insurance_category_created_at')
    updated_at = models.DateTimeField(auto_now=True, db_column='insurance_category_updated_at')
    status = models.CharField(max_length=10, default='Active', db_column='insurance_category_status')

    class Meta:
        db_table = 'ni_insurance_category'
        verbose_name = 'Insurance Category'
        verbose_name_plural = 'Insurance Categories'

    def __str__(self):
        return self.name


class InsuranceProduct(models.Model):
    id = models.AutoField(primary_key=True, db_column='product_id')
    name = models.CharField(max_length=150, db_column='insurance_product_name')
    insurance_type = models.ForeignKey(
        InsuranceType,
        on_delete=models.CASCADE,
        db_column='insurance_type_id',
        related_name='products'
    )
    category = models.ForeignKey(
        InsuranceCategory,
        on_delete=models.CASCADE,
        db_column='category_id',
        related_name='products'
    )
    created_at = models.DateTimeField(auto_now_add=True, db_column='insurance_product_created_at')
    updated_at = models.DateTimeField(auto_now=True, db_column='insurance_product_updated_at')
    status = models.CharField(max_length=10, default='Active', db_column='insurance_product_status')

    class Meta:
        db_table = 'ni_insurance_product'
        verbose_name = 'Insurance Product'
        verbose_name_plural = 'Insurance Products'

    def __str__(self):
        return self.name
