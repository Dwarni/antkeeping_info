from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('<str:country_code>/', views.index, name='country')
]
