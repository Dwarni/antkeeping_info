"""
    url module for api app
"""
from django.urls import path

from . import views

urlpatterns = [
    path('ants/',
         views.AntSpeciesListView.as_view(),
         name='api_ant_species'),
    path('ants/nuptial-flight-months/',
         views.NuptialFlightMonths.as_view(),
         name='api_ants_nuptial_flight_month'),
    path('ants/<str:ant_species>/',
         views.AntSpeciesDetailView.as_view(), name='api_ant_species_detail'),
    path('genera/',
         views.GeneraListView.as_view(),
         name='api_genera'
         ),
    path('genera/<int:id>/ants/',
         views.AntsByGenusView.as_view(),
         name='api_ants_by_genus'
         ),
    path('regions/', views.RegionsView.as_view(), name='api_regions'),
    path('regions/<str:region>/',
         views.RegionView.as_view(), name='api_region'),
    path('regions/<str:region>/ants/',
         views.AntsByRegionView.as_view(), name='api_ants_by_region'),
    path('regions/<str:region>/ants/diff/<str:region2>/',
         views.AntsByRegionDiffView.as_view(), name='api_ants_by_region_diff'),
    path('regions/<str:region>/ants/common/<str:region2>/',
         views.AntsByRegionCommonView.as_view(),
         name='api_ants_by_region_common')
]
