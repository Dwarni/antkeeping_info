"""
    url module for ants app
"""
from django.urls import path, register_converter

from . import converters, views

register_converter(converters.CaseInsensitiveSlugConverter, 'islug')

urlpatterns = [
    path('ant-species-autocomplete/',
         views.AntSpeciesAutocomplete.as_view(),
         name='ant_species_autocomplete'),
    path('<islug:slug>/', views.AntSpeciesDetail.as_view(), name='ant_detail'),
]
