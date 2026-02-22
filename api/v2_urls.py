from django.urls import path
from . import v2_views

urlpatterns = [
    path("ants/", v2_views.AntSpeciesListView.as_view(), name="v2_api_ant_species"),
    path(
        "ants/nuptial-flight-months/",
        v2_views.NuptialFlightMonths.as_view(),
        name="v2_api_ants_nuptial_flight_month",
    ),
    path(
        "ants/<str:ant_species>/",
        v2_views.AntSpeciesDetailView.as_view(),
        name="v2_api_ant_species_detail",
    ),
    path("regions/", v2_views.RegionListView.as_view(), name="v2_api_regions"),
]
