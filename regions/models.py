from django.db import models
from django.utils.translation import ugettext as _


# Create your models here.
class BaseRegion(models.Model):
    """Base region class"""
    code = models.CharField(
        max_length=8,
        verbose_name='ISO Code',
        db_index=True
    )
    name = models.CharField(max_length=200)
    ant_list_complete = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    class Meta:
        abstract = True
        ordering = ['name']


class Country(BaseRegion):
    """Represents a country"""
    class Meta:
        verbose_name = _('Country')
        verbose_name_plural = _('Countries')


class Region(BaseRegion):
    """Represents a Region within a country.

    Can be a state, canton (Switzerland), department (France) etc.

    Each region always belongs to one country.
    """
    country = models.ForeignKey(Country, on_delete=models.CASCADE)
    type = models.CharField(max_length=100)

    class Meta:
        verbose_name = _('Region')
        verbose_name_plural = _('Regions')
        ordering = ['country', 'name']

    def __str__(self):
        return self.country.name + ' - ' + self.name
