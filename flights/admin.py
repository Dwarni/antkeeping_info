"""Admin module for flights app."""
from django.contrib import admin
from .models import Flight

# Register your models here.
admin.site.register(Flight)
