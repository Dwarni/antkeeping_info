"""Module for urls of flights app."""
from django.urls import path

from . import views

urlpatterns = [
    path('', views.FlightsMapView.as_view(), name='flights_map'),
    path('add/', views.AddFlightView.as_view(), name='flight_add'),
    path('list', views.FlightsListView.as_view(), name='flights_list'),
    path('<int:pk>/info-window', views.FlightInfoWindow.as_view(), name='flight_info_window')
]
