from django.urls import path

from . import views

urlpatterns = [
    path('ants-by-country', views.AntsByRegion.as_view(),
         name='ant_species_by_country'),
]
