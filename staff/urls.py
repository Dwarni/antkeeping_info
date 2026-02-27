"""
url module for staff app
"""

from django.urls import path

from . import views

urlpatterns = [
    path(
        "add-antspecies-to-region/",
        views.AddAntspeciesToRegionView.as_view(),
        name="staff_add_antspecies_to_region",
    )
]
