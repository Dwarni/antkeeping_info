"""Module for urls of flights app."""
from django.urls import path

from . import views

urlpatterns = [
    path('', views.FlightsMapView.as_view(), name='flights_map'),
    path('add/', views.AddFlightView.as_view(), name='flight_add'),
    path('list/', views.FlightsListView.as_view(), name='flights_list'),
    path('mating-chart/', views.MatingChartView.as_view(),
         name='flights_mating_chart'),
    path(
        'review/', views.FlightsReviewListView.as_view(),
        name='flights_review_list'),
    path(
        '<int:pk>/info-window', views.FlightInfoWindow.as_view(),
        name='flight_info_window'),
    path(
        '<int:pk>/review', views.FlightReviewView.as_view(),
        name='flight_review'),
    path(
        '<int:pk>/delete', views.FlightDeleteView.as_view(),
        name='flight_delete'),
    path(
        'habitat-tags-autocomplete', views.HabitatTagAutocomplete.as_view(),
        name='flight_habitat_tags_autocomplete'
    ),
    path(
        'top-lists', views.TopLists.as_view(),
        name='flights_top_lists'
    )
]
