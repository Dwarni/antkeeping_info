from django.db import models
from django.utils.translation import ugettext as _


# Create your models here.
class Region(models.Model):
    """Represents a Region.

    A region can be a country, state, geoscheme, biogeographic realm etc.
    """
    code = models.CharField(
        max_length=8,
        verbose_name='ISO Code',
        db_index=True
    )
    name = models.CharField(max_length=200)
    official_name = models.CharField(max_length=200, blank=True, null=True)

    type = models.CharField(max_length=100)

    parent = models.ForeignKey(
        'Region',
        models.SET_NULL,
        blank=True,
        null=True,
        related_name='children'
    )

    class Meta:
        verbose_name = _('Region')
        verbose_name_plural = _('Regions')
        ordering = ['type', 'name']

    def __str__(self):
        country = None
        if self.parent and self.parent.type == 'Country':
            country = self.parent.name

        if country:
            return '%s (%s, %s)' % (self.name, self.type, country)
        else:
            return '%s (%s)' % (self.name, self.type)
