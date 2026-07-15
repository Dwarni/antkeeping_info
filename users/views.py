"""
Module for views of users app.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.conf import settings
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.generic import TemplateView

from allauth.socialaccount.models import SocialApp
from allauth.socialaccount.views import ConnectionsView

SOCIAL_PROVIDERS = [
    {"id": "discord", "name": "Discord", "icon": "bi-discord"},
    {"id": "google", "name": "Google", "icon": "bi-google"},
]


def _build_profile_food_ratings_context(user):
    return {
        "food_rating_submissions": (
            user.food_rating_submissions
            .prefetch_related("species_food_ratings__species", "photos")
            .order_by("-updated_at")
        ),
    }


@method_decorator(never_cache, name="dispatch")
class UserProfileView(LoginRequiredMixin, TemplateView):
    """User profile view."""

    template_name = "users/profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        connected = {
            sa.provider: sa
            for sa in self.request.user.socialaccount_set.all()
        }
        configured = set(
            SocialApp.objects.filter(sites__id=settings.SITE_ID)
            .values_list("provider", flat=True)
        )
        providers = [
            {
                **p,
                "account": connected.get(p["id"]),
                "configured": p["id"] in configured,
            }
            for p in SOCIAL_PROVIDERS
        ]
        context["social_providers"] = providers
        context["can_disconnect"] = self.request.user.has_usable_password
        context["difficulty_ratings"] = (
            self.request.user.difficulty_ratings.select_related("species").order_by("-updated_at")
        )
        context.update(_build_profile_food_ratings_context(self.request.user))
        return context


@method_decorator(never_cache, name="dispatch")
class UserProfileFoodRatingsView(LoginRequiredMixin, TemplateView):
    """HTMX fragment: just the 'Your food ratings' list, refreshed after an edit."""

    template_name = "users/profile_food_ratings_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_build_profile_food_ratings_context(self.request.user))
        return context


class ProfileDisconnectView(ConnectionsView):
    """Disconnect a social account and redirect back to the profile page."""

    success_url = reverse_lazy("user_profile")
