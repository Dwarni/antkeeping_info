"""Module which contains all views of flights app."""

import logging

from dal import autocomplete
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.contenttypes.models import ContentType
from django.db.models import Count, F, Func, Value
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.generic import (
    DeleteView,
    DetailView,
    ListView,
    TemplateView,
    View,
)
from taggit.models import Tag

from ants.views import add_iframe_to_context

from .models import Flight

logger = logging.getLogger(__name__)

# Create your views here.


@method_decorator(xframe_options_exempt, name="dispatch")
class FlightsMapView(TemplateView):
    """View for the flights map."""

    template_name = "flights/flights_map.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["years"] = [
            d.year for d in Flight.objects.all().dates("date", "year", order="DESC")
        ]
        add_iframe_to_context(context, self.request)
        return context


@method_decorator(never_cache, name="dispatch")
class FlightsListView(ListView):
    """List view for flights."""

    model = Flight

    def get(self, request, *args, **kwargs):
        qs = self.get_queryset()
        year = request.GET.get("year")
        if year and year != "all":
            qs = qs.filter(date__year=year)
        qs = qs.values("id", "latitude", "longitude", "ant_species__name")
        data = [
            {
                "id": flight.get("id"),
                "lat": flight.get("latitude"),
                "lng": flight.get("longitude"),
                "ant": flight.get("ant_species__name"),
            }
            for flight in qs
        ]
        return JsonResponse(data, status=200, safe=False)


class FlightInfoWindow(DetailView):
    """View for google maps info window."""

    template_name = "flights/info_window.html"
    model = Flight
    context_object_name = "flight"


@method_decorator(staff_member_required, name="dispatch")
@method_decorator(never_cache, name="dispatch")
class FlightsReviewListView(ListView):
    """Displays all not yet reviewed flights."""

    model = Flight
    template_name = "flights/flights_review.html"
    queryset = model.objects.filter(reviewed=False).select_related(
        "ant_species", "country"
    )
    context_object_name = "flights"


@method_decorator(staff_member_required, name="dispatch")
class FlightReviewView(View):
    def post(self, request, **kwargs):
        """Handels the post request."""
        pk = kwargs.get("pk")
        flight = get_object_or_404(Flight, pk=pk)
        flight.reviewed = True
        flight.save()

        return redirect("flights_review_list")


@method_decorator(staff_member_required, name="dispatch")
class FlightDeleteView(DeleteView):
    model = Flight
    success_url = reverse_lazy("flights_review_list")


class FlightStatisticView(TemplateView):
    template_name = "flights/flight_statistic.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ants = (
            Flight.objects.values("ant_species__slug", "ant_species__name")
            .distinct()
            .order_by("ant_species__name")
        )
        context["ants"] = ants
        return context


class HabitatTagAutocomplete(autocomplete.Select2QuerySetView):
    """QuerySetView for flight habitat autocomplete."""

    def get_queryset(self):
        flight_content_type = ContentType.objects.get(
            app_label="flights", model="flight"
        )
        qs = Tag.objects.filter(
            taggit_taggeditem_items__content_type=flight_content_type
        )

        if self.q:
            qs = qs.filter(name__istartswith=self.q)

        return qs.distinct().order_by("name")


class MatingChartView(TemplateView):
    """Kept for backwards compatibility – redirects to the new nuptial flight table."""

    def get(self, request, *args, **kwargs):
        from django.urls import reverse

        return redirect(reverse("nuptial_flight_table"), permanent=True)


class RegexpReplace(Func):
    function = "REGEXP_REPLACE"

    def __init__(self, expression, pattern, replacement, **extra):
        if not hasattr(pattern, "resolve_expression"):
            if not isinstance(pattern, str):
                raise TypeError("'pattern' must be a string")
            pattern = Value(pattern)
        if not hasattr(replacement, "resolve_expression"):
            if not isinstance(replacement, str):
                raise TypeError("'replacement' must be a string")
            replacement = Value(replacement)
        expressions = [expression, pattern, replacement]
        super().__init__(*expressions, **extra)


class TopLists(TemplateView):
    template_name = "flights/top_lists/top_lists.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = Flight.objects
        self.add_top_external_users(qs, context)
        self.add_top_external_websites(qs, context)
        self.add_top_species(qs, context)
        self.add_top_countries(qs, context)

        return context

    def add_top_external_users(self, query_set, context):
        flights = query_set.filter(external_user__isnull=False).order_by(
            "external_user", "link", "date"
        )

        external_users = []
        last_username = None
        last_hostname = None
        for flight in flights:
            if (
                flight.external_user != last_username
                or flight.link_host != last_hostname
            ):
                last_username = flight.external_user
                last_hostname = flight.link_host
                external_user = {}
                external_user["name"] = last_username
                external_user["hostname"] = last_hostname
                external_user["flight_count"] = 0
                external_users.append(external_user)

            last_external_user = external_users[-1]
            last_external_user["flight_count"] += 1

        external_users.sort(
            key=lambda external_user: external_user["flight_count"], reverse=True
        )
        context["external_users"] = external_users[:10]
        context["max_flights"] = external_users[0]["flight_count"]

    def add_top_external_websites(self, query_set, context):
        flights = query_set.exclude(link__isnull=True).order_by("link", "date")

        websites = []
        last_website_name = None
        for flight in flights:
            if flight.link_host != last_website_name:
                last_website_name = flight.link_host
                website = {}
                website["name"] = last_website_name
                website["count"] = 0
                websites.append(website)

            if len(websites) > 1:
                last_website = websites[-1]
                last_website["count"] += 1

        websites.sort(key=lambda website: website["count"], reverse=True)
        context["top_websites"] = websites
        context["top_websites_max_reports"] = websites[0]["count"]

    def add_top_species(self, query_set, context):
        species = (
            query_set.values(name=F("ant_species__name"))
            .annotate(count=Count("name"))
            .order_by("-count")
        )[:10]
        context["top_species"] = species
        context["top_species_max_reports"] = species.first()["count"]

    def add_top_countries(self, query_set, context):
        countries = (
            query_set.values(name=F("country__name"))
            .annotate(count=Count("name"))
            .order_by("-count")
        )[:10]
        context["top_countries"] = countries
        context["top_countries_max_reports"] = countries.first()["count"]
