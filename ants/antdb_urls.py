from django.urls import path

from . import views

urlpatterns = [
    path('ant-species-by-region', views.AntSpeciesByRegion.as_view(),
         name='ant_species_by_region'),
]
