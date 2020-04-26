"""
    url module for flights api
"""
from django.urls import path
from django.http import HttpResponse

from api.flights.views import flights, years

urlpatterns = [
    path('hello', lambda request: HttpResponse(
        'Hello World!'), name="hello_world"),
    path('years', years, name="api_flight_years"),
    path('', flights, name="api_flights")
]
