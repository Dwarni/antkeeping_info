from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext as _


# Create your models here.
class Region(models.Model):
    """Represents a Region.

    A region can be a country, state, geoscheme, biogeographic realm etc.
    """

    code = models.CharField(
        max_length=8, verbose_name="ISO Code", db_index=True, blank=True, null=True
    )
    name = models.CharField(max_length=200)
    official_name = models.CharField(max_length=200, blank=True, null=True)
    slug = models.SlugField(db_index=True, editable=False)

    type = models.CharField(max_length=100)

    parent = models.ForeignKey(
        "Region", models.SET_NULL, blank=True, null=True, related_name="children"
    )

    class Meta:
        verbose_name = _("Region")
        verbose_name_plural = _("Regions")
        ordering = ["type", "name"]

    def __str__(self):
        return "%s (%s)" % (self.name, self.type)

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        self.slug = slugify(self.name)
        super().save(force_insert, force_update, using, update_fields)
