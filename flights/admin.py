"""Admin module for flights app."""
from django.contrib import admin
from .models import Flight, Temperature, Velocity


@admin.register(Temperature)
class TemperatureAdmin(admin.ModelAdmin):
    pass


@admin.register(Velocity)
class VelocityAdmin(admin.ModelAdmin):
    pass


@admin.register(Flight)
class FlightAdmin(admin.ModelAdmin):
    search_fields = ['ant_species__name', 'address', 'date', 'link']
