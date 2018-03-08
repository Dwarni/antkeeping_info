from django.urls import path

from . import views

urlpatterns = [
    path('<str:slug>/', views.AntSpeciesDetail.as_view(), name='ant_detail')
]