"""
url module for users app
"""

from django.urls import path

from .views import (
    ProfileDisconnectView,
    UserProfileAvatarDeleteView,
    UserProfileColoniesView,
    UserProfileDifficultyRatingsView,
    UserProfileFoodRatingsView,
    UserProfileJournalsView,
    UserProfileSettingsView,
    UserProfileView,
)

urlpatterns = [
    path("profile/", UserProfileView.as_view(), name="user_profile"),
    path("profile", UserProfileView.as_view()),
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
    path(
        "profile/settings/",
        UserProfileSettingsView.as_view(),
        name="user_profile_settings",
    ),
    path(
        "profile/avatar/delete/",
        UserProfileAvatarDeleteView.as_view(),
        name="user_profile_avatar_delete",
    ),
    path("disconnect/", ProfileDisconnectView.as_view(), name="profile_disconnect"),
]
