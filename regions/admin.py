from django.contrib import admin
from regions.models import Country, Region


# Register your models here.
class BaseRegionAdmin(admin.ModelAdmin):
    search_fields = ["name"]


@admin.register(Region)
class RegionAdmin(BaseRegionAdmin):
    pass


@admin.register(Country)
class CountryAdmin(BaseRegionAdmin):
    pass
