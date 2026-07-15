"""
url module for users app
"""

from django.urls import path

from .views import ProfileDisconnectView, UserProfileFoodRatingsView, UserProfileView

urlpatterns = [
    path("profile", UserProfileView.as_view(), name="user_profile"),
    path("profile/food-ratings/", UserProfileFoodRatingsView.as_view(), name="user_profile_food_ratings"),
    path("disconnect/", ProfileDisconnectView.as_view(), name="profile_disconnect"),
]
