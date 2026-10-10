"""
url module for users app
"""

from django.urls import path

from .views import (
    ProfileDisconnectView,
    UserProfileColoniesView,
    UserProfileDifficultyRatingsView,
    UserProfileFoodRatingsView,
    UserProfileJournalsView,
    UserProfileView,
)

urlpatterns = [
    path("profile", UserProfileView.as_view(), name="user_profile"),
    path(
        "profile/colonies/",
        UserProfileColoniesView.as_view(),
        name="user_profile_colonies",
    ),
    path(
        "profile/journals/",
        UserProfileJournalsView.as_view(),
        name="user_profile_journals",
    ),
    path(
        "profile/food-ratings/",
        UserProfileFoodRatingsView.as_view(),
        name="user_profile_food_ratings",
    ),
    path(
        "profile/difficulty-ratings/",
        UserProfileDifficultyRatingsView.as_view(),
        name="user_profile_difficulty_ratings",
    ),
    path("disconnect/", ProfileDisconnectView.as_view(), name="profile_disconnect"),
]
