from django.db import models
from django.utils.translation import ugettext as _


# Create your models here.
class Country(models.Model):
    code = models.CharField(
        max_length=3,
        verbose_name='Country code',
        db_index=True
    )
    name = models.CharField(max_length=200)
    ant_list_complete = models.BooleanField(default=False)

    class Meta:
        verbose_name = _('Country')
        verbose_name_plural = _('Countries')
        ordering = ['name']

    def __str__(self):
        return self.name


class Region(models.Model):
    name = models.CharField(max_length=200)
    country = models.ForeignKey(Country, on_delete=models.CASCADE)
    type = models.CharField(max_length=100)
    code = models.CharField(max_length=20, db_index=True)
    ant_list_complete = models.BooleanField(default=False)

    class Meta:
        verbose_name = _('Region')
        verbose_name_plural = _('Regions')
        ordering = ['country', 'name']

    def __str__(self):
        return self.country.name + ' - ' + self.name