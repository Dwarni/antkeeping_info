from django.urls import path

from . import views

urlpatterns = [
    path('<slug:slug>/', views.AntSpeciesDetail.as_view(), name='ant_detail')
]