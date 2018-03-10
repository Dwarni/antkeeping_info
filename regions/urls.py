from django.urls import path

from . import views

urlpatterns = [
    path('', views.CountryIndex.as_view(), name='index'),
    path('<str:country_code>/', views.CountryAntList.as_view(), name='country')
]
