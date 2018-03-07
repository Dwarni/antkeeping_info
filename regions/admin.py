from django.contrib import admin
from regions.models import Country, Region


# Register your models here.
@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    pass


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    pass
