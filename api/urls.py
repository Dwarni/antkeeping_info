"""
    url module for api app
"""
from django.urls import path, include

from django.views.generic import TemplateView

from rest_framework.schemas import get_schema_view

from . import views

urlpatterns = [
    path('schema', get_schema_view(
         title="Antkeeping.info API",
         version="1.0.0"
         ), name='api-schema'),
    path('doc', TemplateView.as_view(
        template_name='swagger_ui.html',
        extra_context={'schema_url': 'api-schema'}
    ), name='api-doc'),
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
         name='api_ants_by_region_common'),
    path('flights/', include('api.flights.urls'))
]
