"""
    url module for ants app
"""
from django.urls import path, register_converter

from . import converters, views

register_converter(converters.CaseInsensitiveSlugConverter, 'islug')

urlpatterns = [
    path('keeping-forbidden-in-eu-species/', views.ForbiddenInEUSpeciesListView.as_view(), name='forbidden_in_eu_species_list'),
    path('ant-species-autocomplete/',
         views.AntSpeciesAutocomplete.as_view(),
         name='ant_species_autocomplete'),
    path('<islug:slug>/', views.AntSpeciesDetail.as_view(), name='ant_detail'),
]
