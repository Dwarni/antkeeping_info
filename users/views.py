"""
views module for users app.
"""

import datetime

from allauth.socialaccount.models import SocialApp
from allauth.socialaccount.views import ConnectionsView
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Count
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.decorators.cache import never_cache
from django.views.generic import TemplateView

from ants.models import Colony, ColonyJournalEntry, SpeciesFoodRating
from ants.views import _annotate_journal_entries

from .forms import UserProfileSettingsForm
from .models import UserProfile

SOCIAL_PROVIDERS = [
    {"id": "discord", "name": "Discord", "icon": "bi-discord"},
    {"id": "google", "name": "Google", "icon": "bi-google"},
]


class ProfileContextMixin:
    """Helper mixin to inject profile navigation counts and profile object into views."""

    def get_profile_nav_context(self, user):
        profile = getattr(user, "profile", None)
        if profile is None and user.is_authenticated:
            profile = UserProfile.objects.get_or_create(user=user)[0]
        return {
            "profile": profile,
            "colonies_count": user.colonies.count(),
            "journal_entries_count": ColonyJournalEntry.objects.filter(
                colony__user=user
            ).count(),
            "food_ratings_count": user.food_ratings.count(),
            "difficulty_ratings_count": user.difficulty_ratings.count(),
        }


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
class UserProfileView(LoginRequiredMixin, ProfileContextMixin, TemplateView):
    """User profile main dashboard view."""

    template_name = "users/profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_profile_nav_context(self.request.user))
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
        context["has_usable_password"] = self.request.user.has_usable_password

        colonies_qs = self.request.user.colonies.select_related(
            "species", "title_image"
        ).order_by("-created_at")
        difficulty_ratings_qs = self.request.user.difficulty_ratings.select_related(
            "species"
        ).order_by("-updated_at")

        context["colonies"] = colonies_qs
        context["difficulty_ratings"] = difficulty_ratings_qs
        context.update(_build_profile_food_ratings_context(self.request.user))
        return context


@method_decorator(never_cache, name="dispatch")
class UserProfileColoniesView(LoginRequiredMixin, ProfileContextMixin, TemplateView):
    """Subpage: User's ant colonies overview and management."""

    template_name = "users/profile_colonies.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_profile_nav_context(self.request.user))
        all_colonies = (
            self.request.user.colonies.select_related("species", "title_image")
            .prefetch_related("censuses")
            .annotate(journal_entries_count=Count("journal_entries", distinct=True))
            .order_by("-created_at")
        )
        status_filter = self.request.GET.get("status", "").strip().lower()
        if status_filter == "active":
            colonies = [c for c in all_colonies if c.status == Colony.ACTIVE]
        elif status_filter == "founding":
            colonies = [c for c in all_colonies if c.status == Colony.FOUNDING]
        elif status_filter == "hibernating":
            colonies = [c for c in all_colonies if c.status == Colony.HIBERNATING]
        elif status_filter == "archived":
            colonies = [
                c for c in all_colonies if c.status in (Colony.DEAD, Colony.GIVEN_AWAY)
            ]
        else:
            status_filter = ""
            colonies = list(all_colonies)

        context["colonies"] = colonies
        context["current_status_filter"] = status_filter
        context["total_colonies"] = len(all_colonies)
        context["active_colonies"] = sum(
            1 for c in all_colonies if c.status == Colony.ACTIVE
        )
        context["founding_colonies"] = sum(
            1 for c in all_colonies if c.status == Colony.FOUNDING
        )
        context["hibernating_colonies"] = sum(
            1 for c in all_colonies if c.status == Colony.HIBERNATING
        )
        context["archived_colonies"] = sum(
            1 for c in all_colonies if c.status in (Colony.DEAD, Colony.GIVEN_AWAY)
        )
        context["public_colonies"] = sum(1 for c in all_colonies if c.is_public)
        return context


@method_decorator(never_cache, name="dispatch")
class UserProfileJournalsView(LoginRequiredMixin, ProfileContextMixin, View):
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

        render_context = self.get_profile_nav_context(user)
        render_context.update(
            {
                "page_obj": page_obj,
                "colonies": colonies,
                "selected_colony": selected_colony,
                "selected_colony_id": colony_id,
                "current_event_type": event_type,
                "event_types": ColonyJournalEntry.EVENT_TYPE_CHOICES,
                "total_entries": total_entries,
                "has_colonies": colonies.exists(),
            }
        )
        return render(request, "users/profile_journals.html", render_context)


@method_decorator(never_cache, name="dispatch")
class UserProfileFoodRatingsView(LoginRequiredMixin, ProfileContextMixin, TemplateView):
    """Subpage & HTMX fragment: user's food acceptance ratings."""

    template_name = "users/profile_food_ratings.html"

    def get_template_names(self):
        if self.request.headers.get("HX-Request"):
            return ["users/profile_food_ratings_list.html"]
        return [self.template_name]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_profile_nav_context(self.request.user))
        context.update(_build_profile_food_ratings_context(self.request.user))
        return context


@method_decorator(never_cache, name="dispatch")
class UserProfileDifficultyRatingsView(
    LoginRequiredMixin, ProfileContextMixin, TemplateView
):
    """Subpage: user's ant species keeping difficulty ratings."""

    template_name = "users/profile_difficulty_ratings.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_profile_nav_context(self.request.user))
        ratings = self.request.user.difficulty_ratings.select_related(
            "species"
        ).order_by("-updated_at")
        context["difficulty_ratings"] = ratings
        context["total_count"] = ratings.count()
        return context


@method_decorator(never_cache, name="dispatch")
class UserProfileSettingsView(LoginRequiredMixin, ProfileContextMixin, View):
    """Subpage: User profile settings, avatar upload, and account security hub."""

    template_name = "users/profile_settings.html"

    def get_social_providers(self, user):
        connected = {sa.provider: sa for sa in user.socialaccount_set.all()}
        configured = set(
            SocialApp.objects.filter(sites__id=settings.SITE_ID).values_list(
                "provider", flat=True
            )
        )
        return [
            {
                **p,
                "account": connected.get(p["id"]),
                "configured": p["id"] in configured,
            }
            for p in SOCIAL_PROVIDERS
        ]

    def get(self, request):
        form = UserProfileSettingsForm(user=request.user)
        context = self.get_profile_nav_context(request.user)
        context.update(
            {
                "form": form,
                "has_usable_password": request.user.has_usable_password(),
                "can_disconnect": request.user.has_usable_password(),
                "social_providers": self.get_social_providers(request.user),
                "email_addresses": request.user.emailaddress_set.all(),
            }
        )
        return render(request, self.template_name, context)

    def post(self, request):
        form = UserProfileSettingsForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, _("Your profile settings have been updated."))
            return redirect("user_profile_settings")

        context = self.get_profile_nav_context(request.user)
        context.update(
            {
                "form": form,
                "has_usable_password": request.user.has_usable_password(),
                "can_disconnect": request.user.has_usable_password(),
                "social_providers": self.get_social_providers(request.user),
                "email_addresses": request.user.emailaddress_set.all(),
            }
        )
        messages.error(request, _("Please correct the errors in the form."))
        return render(request, self.template_name, context, status=400)


@method_decorator(never_cache, name="dispatch")
class UserProfileAvatarDeleteView(LoginRequiredMixin, View):
    """Action: Remove the current user's profile avatar."""

    def post(self, request):
        profile = UserProfile.objects.get_or_create(user=request.user)[0]
        if profile.avatar:
            profile.avatar.delete(save=False)
            profile.avatar = None
            profile.save()
            messages.success(request, _("Your avatar has been removed."))
        return redirect("user_profile_settings")


class ProfileDisconnectView(ConnectionsView):
    """Disconnect a social account and redirect back to the profile page."""

    success_url = reverse_lazy("user_profile")
