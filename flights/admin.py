"""Admin module for flights app."""
from django.contrib import admin
from .models import Flight

@admin.register(Flight)
class FlightAdmin(admin.ModelAdmin):
    search_fields = ['ant_species__name', 'address', 'date', 'link']
