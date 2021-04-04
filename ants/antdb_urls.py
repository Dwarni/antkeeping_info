from django.urls import path

from . import views

urlpatterns = [
    path('ants-by-country', views.AntsByCountry.as_view(),
         name='ants_by_country'),
]
