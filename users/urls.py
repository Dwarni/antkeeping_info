"""
url module for users app
"""

from django.contrib.auth import views as auth_views
from django.urls import path

from .forms import CustomAuthentificationForm
from .views import UserProfileView

urlpatterns = [
    path(
        "login",
        auth_views.LoginView.as_view(
            template_name="users/login.html",
            authentication_form=CustomAuthentificationForm,
        ),
        name="login",
    ),
    path("logout", auth_views.LogoutView.as_view(), name="logout"),
    path("profile", UserProfileView.as_view(), name="user_profile"),
]
