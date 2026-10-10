"""
Module for views of users app.
"""

from allauth.socialaccount.models import SocialApp
from allauth.socialaccount.views import ConnectionsView
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Count
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import never_cache
from django.views.generic import TemplateView

from ants.models import Colony, ColonyJournalEntry, SpeciesFoodRating
from ants.views import _annotate_journal_entries

SOCIAL_PROVIDERS = [
    {"id": "discord", "name": "Discord", "icon": "bi-discord"},
    {"id": "google", "name": "Google", "icon": "bi-google"},
]


def _build_profile_food_ratings_context(user):
    food_ratings = user.food_ratings.select_related("species", "food_item").order_by(
        "-updated_at"
    )
    return {
        "food_ratings": food_ratings,
        "food_ratings_count": food_ratings.count(),
        "food_upvotes_count": food_ratings.filter(vote=SpeciesFoodRating.UP).count(),
        "food_downvotes_count": food_ratings.filter(
            vote=SpeciesFoodRating.DOWN
        ).count(),
    }


@method_decorator(never_cache, name="dispatch")
class UserProfileView(LoginRequiredMixin, TemplateView):
    """User profile main dashboard view."""

    template_name = "users/profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        connected = {
            sa.provider: sa for sa in self.request.user.socialaccount_set.all()
        }
        configured = set(
            SocialApp.objects.filter(sites__id=settings.SITE_ID).values_list(
                "provider", flat=True
            )
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

        colonies_qs = self.request.user.colonies.select_related(
            "species", "title_image"
        ).order_by("-created_at")
        difficulty_ratings_qs = self.request.user.difficulty_ratings.select_related(
            "species"
        ).order_by("-updated_at")
        journal_entries_count = ColonyJournalEntry.objects.filter(
            colony__user=self.request.user
        ).count()

        context["colonies"] = colonies_qs
        context["colonies_count"] = colonies_qs.count()
        context["difficulty_ratings"] = difficulty_ratings_qs
        context["difficulty_ratings_count"] = difficulty_ratings_qs.count()
        context["journal_entries_count"] = journal_entries_count
        context.update(_build_profile_food_ratings_context(self.request.user))
        return context


@method_decorator(never_cache, name="dispatch")
class UserProfileColoniesView(LoginRequiredMixin, TemplateView):
    """Subpage: User's ant colonies overview and management."""

    template_name = "users/profile_colonies.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        colonies = (
            self.request.user.colonies.select_related("species", "title_image")
            .annotate(journal_entries_count=Count("journal_entries", distinct=True))
            .order_by("-created_at")
        )
        context["colonies"] = colonies
        context["total_colonies"] = colonies.count()
        context["active_colonies"] = sum(
            1 for c in colonies if c.status == Colony.ACTIVE
        )
        context["public_colonies"] = sum(1 for c in colonies if c.is_public)
        return context


@method_decorator(never_cache, name="dispatch")
class UserProfileJournalsView(LoginRequiredMixin, View):
    """Subpage: User's journal entries timeline across their colonies with filtering."""

    RESULTS_PER_PAGE = 15

    def get(self, request):
        user = request.user
        colonies = (
            user.colonies.select_related("species", "title_image")
            .annotate(journal_count=Count("journal_entries", distinct=True))
            .order_by("name")
        )

        qs = (
            ColonyJournalEntry.objects.filter(colony__user=user)
            .select_related("colony", "colony__species", "colony__user")
            .prefetch_related("images")
        )
        qs = _annotate_journal_entries(qs, user)

        colony_id = request.GET.get("colony", "").strip()
        selected_colony = None
        if colony_id.isdigit():
            selected_colony = colonies.filter(pk=int(colony_id)).first()
            if selected_colony:
                qs = qs.filter(colony=selected_colony)

        event_type = request.GET.get("event_type", "").strip()
        if event_type:
            qs = qs.filter(event_type=event_type)

        qs = qs.order_by("-date", "-created_at")
        total_entries = qs.count()
        paginator = Paginator(qs, self.RESULTS_PER_PAGE)
        page_obj = paginator.get_page(request.GET.get("page", 1))

        return render(
            request,
            "users/profile_journals.html",
            {
                "page_obj": page_obj,
                "colonies": colonies,
                "selected_colony": selected_colony,
                "selected_colony_id": colony_id,
                "current_event_type": event_type,
                "event_types": ColonyJournalEntry.EVENT_TYPE_CHOICES,
                "total_entries": total_entries,
                "has_colonies": colonies.exists(),
            },
        )


@method_decorator(never_cache, name="dispatch")
class UserProfileFoodRatingsView(LoginRequiredMixin, TemplateView):
    """Subpage & HTMX fragment: user's food acceptance ratings."""

    template_name = "users/profile_food_ratings.html"

    def get_template_names(self):
        if self.request.headers.get("HX-Request"):
            return ["users/profile_food_ratings_list.html"]
        return [self.template_name]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_build_profile_food_ratings_context(self.request.user))
        return context


@method_decorator(never_cache, name="dispatch")
class UserProfileDifficultyRatingsView(LoginRequiredMixin, TemplateView):
    """Subpage: user's ant species keeping difficulty ratings."""

    template_name = "users/profile_difficulty_ratings.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ratings = self.request.user.difficulty_ratings.select_related(
            "species"
        ).order_by("-updated_at")
        context["difficulty_ratings"] = ratings
        context["total_count"] = ratings.count()
        return context


class ProfileDisconnectView(ConnectionsView):
    """Disconnect a social account and redirect back to the profile page."""

    success_url = reverse_lazy("user_profile")
