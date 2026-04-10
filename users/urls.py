"""
url module for users app
"""

from django.urls import path

from .views import ProfileDisconnectView, UserProfileView

urlpatterns = [
    path("profile", UserProfileView.as_view(), name="user_profile"),
    path("disconnect/", ProfileDisconnectView.as_view(), name="profile_disconnect"),
]
