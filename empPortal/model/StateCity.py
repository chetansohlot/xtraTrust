from django.db import models

class State(models.Model):
    name = models.CharField(max_length=50)
    country_id = models.IntegerField()

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'states' 

class City(models.Model):
    city = models.CharField(max_length=255)
    state = models.ForeignKey('State', on_delete=models.CASCADE)

    def __str__(self):
        return self.city

    class Meta:
        db_table = 'cities' 