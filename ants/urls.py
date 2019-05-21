"""
    url module for ants app
"""
from django.urls import path

from . import views

urlpatterns = [
    path('ant-species-autocomplete/',
         views.AntSpeciesAutocomplete.as_view(),
         name='ant_species_autocomplete'),
    path('<slug:slug>/', views.AntSpeciesDetail.as_view(), name='ant_detail')
]
