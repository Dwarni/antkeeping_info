from django.urls import path
from . import views

urlpatterns = [
    path("", views.SearchView.as_view(), name="search"),
    path("autocomplete/", views.SearchAutocompleteView.as_view(), name="search_autocomplete"),
]
