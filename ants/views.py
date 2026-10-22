"""
Module for all models of ants app.
"""

import datetime
import json
import logging

from dal import autocomplete
from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import (
    Avg,
    Count,
    Exists,
    ExpressionWrapper,
    F,
    FloatField,
    Max,
    Min,
    OuterRef,
    Q,
    Sum,
)
from django.http import Http404, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.decorators import method_decorator
from django.utils.text import slugify
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic.base import TemplateView, View
from django.views.generic.detail import DetailView
from django.views.generic.edit import FormView

logger = logging.getLogger(__name__)

from flights.models import Flight

from .forms import (
    ColonyCareEventForm,
    ColonyCensusForm,
    ColonyForm,
    ColonyJournalCommentForm,
    ColonyJournalEntryForm,
    FoodItemCreateForm,
    NuptialFlightReportForm,
)
from .models import (
    AntRegion,
    AntSize,
    AntSpecies,
    Colony,
    ColonyCareEvent,
    ColonyCensus,
    ColonyImage,
    ColonyJournalComment,
    ColonyJournalEntry,
    ColonyJournalEntryImage,
    ColonyJournalEntryLike,
    FoodItem,
    Genus,
    SpeciesDifficultyRating,
    SpeciesFoodRating,
    SubFamily,
    Tribe,
)
from .utils.export import export_csv_response, export_json_response

_MONTH_NAMES_SHORT = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
]
_MONTH_NAMES_FULL = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]
# List of (month_number, short_name) tuples for templates
MONTHS = [(i + 1, name) for i, name in enumerate(_MONTH_NAMES_SHORT)]
MONTHS_FULL = [(i + 1, name) for i, name in enumerate(_MONTH_NAMES_FULL)]


def _nuptial_flight_queryset(request):
    """Return a filtered AntSpecies queryset based on GET params."""
    qs = (
        AntSpecies.objects.prefetch_related("flight_months")
        .filter(flight_months__isnull=False, valid=True)
        .order_by("name")
    )

    name = request.GET.get("name", "")
    if len(name) >= 3:
        qs = qs.filter(name__icontains=name)

    # Region: prefer state over country
    state = request.GET.get("state", "all")
    country = request.GET.get("country", "all")
    region_id = None
    if state != "all":
        region_id = state
    elif country != "all":
        region_id = country
    if region_id:
        try:
            qs = qs.filter(distribution__region__id=int(region_id))
        except (ValueError, TypeError):
            qs = qs.filter(distribution__region__code__iexact=region_id)

    month = request.GET.get("month", "all")
    if month == "current":
        month = str(datetime.date.today().month)
    if month != "all":
        try:
            qs = qs.filter(flight_months__id=int(month))
        except (ValueError, TypeError):
            pass

    return qs.distinct()


def _build_entries(page_qs):
    """Convert a queryset page into template-ready dicts."""
    entries = []
    for ant in page_qs:
        flight_month_ids = frozenset(m.id for m in ant.flight_months.all())
        hr = ant.flight_hour_range
        entries.append(
            {
                "name": ant.name,
                "slug": ant.slug,
                "forbidden_in_eu": ant.forbidden_in_eu,
                "flight_months": flight_month_ids,
                "flight_hour_range_lower": hr.lower if hr else None,
                "flight_hour_range_upper": (hr.upper - 1) if hr else None,
                "flight_climate": ant.flight_climate,
                "antwiki_slug": ant.name.replace(" ", "_"),
            }
        )
    return entries


# Create your views here.


def add_iframe_to_context(context, request):
    """
    Get's the 'iframe'-parameter and sets the 'iframe'
    key in the context dictionary accordingly.
    """
    iframe = request.GET.get("iframe", None)
    if iframe and iframe == "true":
        context["iframe"] = True
    else:
        context["iframe"] = False


def ants_by_country(request, country):
    url = f"{reverse('taxonomic_ranks_by_region', args=['species'])}?country={country}"
    return redirect(url, permanent=True)


class NuptialFlightTableView(TemplateView):
    """Main page for the nuptial flight table."""

    template_name = "ants/nuptial_flight_table.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        countries = (
            AntRegion.countries.filter(
                distribution__species__flight_months__isnull=False
            )
            .distinct()
            .order_by("name")
        )
        today = datetime.date.today()
        context["countries"] = countries
        context["months_full"] = MONTHS_FULL
        context["current_month"] = today.month
        context["current_month_name"] = _MONTH_NAMES_FULL[today.month - 1]

        # Read and validate initial filter values from URL params for form pre-fill
        initial_name = self.request.GET.get("name", "")
        initial_month = self.request.GET.get("month", "all")
        initial_country = self.request.GET.get("country", "all")
        initial_state = self.request.GET.get("state", "all")

        valid_months = {"all", "current"} | {str(i) for i in range(1, 13)}
        if initial_month not in valid_months:
            initial_month = "all"

        if initial_country != "all":
            try:
                obj = countries.filter(id=int(initial_country)).first()
            except (ValueError, TypeError):
                obj = countries.filter(code__iexact=initial_country).first()
            if obj is None or not obj.code:
                initial_country = "all"
                initial_state = "all"
            else:
                initial_country = obj.code.lower()

        initial_states = []
        if initial_country != "all":
            initial_states = list(
                AntRegion.states.filter(
                    parent__code__iexact=initial_country,
                    distribution__species__flight_months__isnull=False,
                )
                .distinct()
                .order_by("name")
            )
            if initial_state != "all":
                valid_state_codes = {s.code.lower() for s in initial_states if s.code}
                if initial_state.lower() not in valid_state_codes:
                    initial_state = "all"
                else:
                    initial_state = initial_state.lower()
        else:
            initial_state = "all"

        loc_parts = []
        if initial_country != "all":
            obj = _resolve_region(initial_country)
            if obj:
                loc_parts.append(obj.name)
        if initial_state != "all":
            obj = _resolve_region(initial_state)
            if obj:
                loc_parts.append(obj.name)

        context["initial_name"] = initial_name
        context["initial_month"] = initial_month
        context["initial_country"] = initial_country
        context["initial_state"] = initial_state
        context["initial_states"] = initial_states
        context["initial_location_label"] = ", ".join(loc_parts)
        context["report_form"] = NuptialFlightReportForm()
        return context


@method_decorator(never_cache, name="dispatch")
class NuptialFlightTableRowsView(View):
    """HTMX fragment: paginated table rows + pagination + count.

    When ?print=1 is set, returns all entries using the print template.
    """

    ENTRIES_PER_PAGE = 30

    def get(self, request):
        from django.template.loader import render_to_string

        qs = _nuptial_flight_queryset(request)

        if request.GET.get("print") == "1":
            entries = _build_entries(qs)
            context = self._print_context(request, entries)
            html = render_to_string(
                "ants/nuptial_flight_table_print.html", context, request=request
            )
            return HttpResponse(html, content_type="text/html")

        total = qs.count()
        paginator = Paginator(qs, self.ENTRIES_PER_PAGE)
        page_obj = paginator.get_page(request.GET.get("page", 1))
        entries = _build_entries(page_obj.object_list)
        today = datetime.date.today()
        html = render_to_string(
            "ants/nuptial_flight_table_rows.html",
            {
                "entries": entries,
                "page_obj": page_obj,
                "total": total,
                "months": MONTHS,
                "current_month": today.month,
            },
            request=request,
        )
        return HttpResponse(html, content_type="text/html")

    def _print_context(self, request, entries):
        month = request.GET.get("month", "all")
        if month == "current":
            month = str(datetime.date.today().month)
        month_label = ""
        if month != "all":
            try:
                month_label = _MONTH_NAMES_FULL[int(month) - 1]
            except (ValueError, IndexError):
                pass

        parts = []
        country_id = request.GET.get("country", "all")
        state_id = request.GET.get("state", "all")
        if state_id != "all":
            obj = _resolve_region(state_id)
            if obj:
                parts.append(obj.name)
        elif country_id != "all":
            obj = _resolve_region(country_id)
            if obj:
                parts.append(obj.name)

        return {
            "entries": entries,
            "months": MONTHS,
            "month_label": month_label,
            "location_label": ", ".join(parts),
            "name_filter": request.GET.get("name", ""),
        }


class NuptialFlightTableStatesView(View):
    """HTMX fragment: state <select> options for a given country.

    Also sends HX-Trigger: refreshTable so the table auto-refreshes.
    """

    def get(self, request):
        country_id = request.GET.get("country", "all")
        states = []
        if country_id != "all":
            try:
                parent_filter = {"parent_id": int(country_id)}
            except (ValueError, TypeError):
                parent_filter = {"parent__code__iexact": country_id}
            states = (
                AntRegion.states.filter(
                    distribution__species__flight_months__isnull=False,
                    **parent_filter,
                )
                .distinct()
                .order_by("name")
            )
        from django.template.loader import render_to_string

        html = render_to_string(
            "ants/nuptial_flight_table_states.html",
            {"states": states},
            request=request,
        )
        response = HttpResponse(html, content_type="text/html")
        response["HX-Trigger"] = "refreshTable"
        return response


class NuptialFlightCSVExportView(View):
    """Server-side CSV export with current filter params."""

    def get(self, request):
        qs = _nuptial_flight_queryset(request)
        headers = ["Species"] + _MONTH_NAMES_SHORT + ["Flight time", "Climate"]
        climate_map = {"m": "Moderate", "w": "Warm", "s": "Muggy"}

        def row_getter(ant):
            flight_ids = frozenset(m.id for m in ant.flight_months.all())
            month_flags = ["x" if i + 1 in flight_ids else "" for i in range(12)]
            hr = ant.flight_hour_range
            time_str = f"{hr.lower}-{hr.upper - 1}" if hr else ""
            return (
                [ant.name]
                + month_flags
                + [time_str, climate_map.get(ant.flight_climate, "")]
            )

        filename = _build_export_filename(request)
        return export_csv_response(qs, filename, headers, row_getter)


class NuptialFlightJSONExportView(View):
    """Server-side JSON export with current filter params."""

    def get(self, request):
        qs = _nuptial_flight_queryset(request)
        data = []
        for ant in qs:
            hr = ant.flight_hour_range
            data.append(
                {
                    "id": ant.id,
                    "name": ant.name,
                    "flight_months": sorted(m.id for m in ant.flight_months.all()),
                    "flight_hour_range": {"lower": hr.lower, "upper": hr.upper - 1}
                    if hr
                    else None,
                    "flight_climate": ant.flight_climate,
                    "forbidden_in_eu": ant.forbidden_in_eu,
                }
            )
        return export_json_response(data, _build_export_filename(request))


def _resolve_region(value):
    """Look up AntRegion by code (case-insensitive) or numeric id."""
    try:
        return AntRegion.objects.filter(id=int(value)).first()
    except (ValueError, TypeError):
        return AntRegion.objects.filter(code__iexact=value).first()


def _build_export_filename(request):
    """Build a descriptive filename based on active filters."""
    parts = ["nuptial-flight-table"]
    name = request.GET.get("name", "")
    if len(name) >= 3:
        parts.append(slugify(name))
    country_id = request.GET.get("country", "all")
    state_id = request.GET.get("state", "all")
    if state_id != "all":
        obj = _resolve_region(state_id)
        if obj:
            parts.append(slugify(obj.name))
    elif country_id != "all":
        obj = _resolve_region(country_id)
        if obj:
            parts.append(slugify(obj.name))
    month = request.GET.get("month", "all")
    if month == "current":
        month = str(datetime.date.today().month)
    if month != "all":
        try:
            parts.append(slugify(_MONTH_NAMES_FULL[int(month) - 1]))
        except (ValueError, IndexError):
            pass
    return "-".join(parts)


class TaxonomicRanksByRegion(TemplateView):
    """Let user see which ant species occur in selected regions."""

    template_name = "ants/antdb/ant_species_by_region.html"

    def _get_rank_config(self, taxonomic_rank):
        """Return (name_field, slug_field, rank_class) for a given taxonomic rank."""
        if taxonomic_rank == "genera":
            return "genus__name", "genus__slug", Genus
        if taxonomic_rank == "tribes":
            return "genus__tribe__name", "genus__tribe__slug", Tribe
        if taxonomic_rank == "sub-families":
            return (
                "genus__tribe__sub_family__name",
                "genus__tribe__sub_family__slug",
                SubFamily,
            )
        return "name", "slug", AntSpecies

    def _get_filtered_queryset(self, taxonomic_rank, country, sub_region, name):
        """Return annotated, filtered queryset for a taxonomic rank (no pagination)."""
        name_field, slug_field, rank_class = self._get_rank_config(taxonomic_rank)

        if sub_region:
            qs = AntSpecies.objects.by_region_code_or_id(sub_region).select_related(
                "genus", "genus__tribe", "genus__tribe__sub_family"
            )
        elif country:
            qs = AntSpecies.objects.by_country_code(country).select_related(
                "genus", "genus__tribe", "genus__tribe__sub_family"
            )
        else:
            return None

        qs = qs.annotate(
            taxonomic_rank_name=F(name_field),
            taxonomic_rank_slug=F(slug_field),
        )
        if name:
            qs = qs.filter(taxonomic_rank_name__icontains=name)
        if taxonomic_rank == "tribes":
            qs = qs.exclude(genus__tribe__name="")

        is_species = rank_class == AntSpecies
        if is_species:
            qs = qs.values(
                "id", "taxonomic_rank_name", "taxonomic_rank_slug", "forbidden_in_eu"
            )
        else:
            qs = qs.values("taxonomic_rank_name", "taxonomic_rank_slug")

        return qs.distinct("taxonomic_rank_name").order_by("taxonomic_rank_name")

    def get(self, request, *args, **kwargs):
        export = request.GET.get("export")
        if export in ("csv", "json"):
            return self._handle_export(request, export, **kwargs)
        return super().get(request, *args, **kwargs)

    def _handle_export(self, request, fmt, **kwargs):
        """Return CSV or JSON export response for the current filter."""
        taxonomic_rank = kwargs.get("taxonomic_rank", "species")
        country = request.GET.get("country")
        sub_region = request.GET.get("subRegion")
        name = request.GET.get("name")

        qs = self._get_filtered_queryset(taxonomic_rank, country, sub_region, name)
        if qs is None:
            qs = []

        filename_parts = [f"ant-{taxonomic_rank}"]
        if country:
            country_obj = AntRegion.objects.get_by_id_or_code(country)
            if country_obj:
                filename_parts.append(slugify(country_obj.name))
        if sub_region:
            subregion_obj = AntRegion.objects.get_by_id_or_code(sub_region)
            if subregion_obj:
                filename_parts.append(slugify(subregion_obj.name))
        if name and len(name) >= 3:
            filename_parts.append(slugify(name))
        filename = "-".join(filename_parts)
        _, _, rank_class = self._get_rank_config(taxonomic_rank)
        is_species = rank_class == AntSpecies

        if fmt == "csv":
            if is_species:
                headers = ["Name", "Forbidden in EU"]
                row_getter = lambda item: [  # noqa: E731
                    item["taxonomic_rank_name"],
                    "yes" if item["forbidden_in_eu"] else "no",
                ]
            else:
                headers = ["Name"]
                row_getter = lambda item: [item["taxonomic_rank_name"]]  # noqa: E731
            return export_csv_response(qs, filename, headers, row_getter)

        # JSON
        if is_species:
            data = [
                {
                    "id": item.get("id"),
                    "name": item["taxonomic_rank_name"],
                    "slug": item["taxonomic_rank_slug"],
                    "forbidden_in_eu": item["forbidden_in_eu"],
                }
                for item in qs
            ]
        else:
            data = [
                {
                    "name": item["taxonomic_rank_name"],
                    "slug": item["taxonomic_rank_slug"],
                }
                for item in qs
            ]
        return export_json_response(data, filename)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        taxonomic_rank = kwargs.get("taxonomic_rank")

        country = self.request.GET.get("country")
        sub_region = self.request.GET.get("subRegion")
        name = self.request.GET.get("name")
        _, _, taxonomic_rank_class = self._get_rank_config(taxonomic_rank)

        if name:
            context["name"] = name

        if country:
            context["country"] = country
            country_obj = AntRegion.objects.get_by_id_or_code(country)
            if country_obj:
                context["country_name"] = country_obj.name
            sub_regions = AntRegion.states.with_ants_and_country(country).order_by(
                "name"
            )
            context["sub_regions"] = sub_regions

        if sub_region:
            context["sub_region"] = sub_region
            subregion_obj = AntRegion.objects.get_by_id_or_code(sub_region)
            if subregion_obj:
                context["subregion_name"] = subregion_obj.name

        context["countries"] = AntRegion.countries.with_ants()
        context["taxonomic_rank_type"] = taxonomic_rank_class._meta.verbose_name_plural
        context["taxonomic_rank_type_lower"] = context["taxonomic_rank_type"].lower()

        taxonomic_ranks = self._get_filtered_queryset(
            taxonomic_rank, country, sub_region, name
        )
        is_print = self.request.GET.get("print") == "1"
        context["is_print"] = is_print
        if taxonomic_ranks is not None:
            total = taxonomic_ranks.count()
            per_page = max(1, total) if is_print else 50
            paginator = Paginator(taxonomic_ranks, per_page)
            page_number = None if is_print else self.request.GET.get("page")
            page_obj = paginator.get_page(page_number)
            context["page_obj"] = page_obj
            context["total_objects"] = total

        add_iframe_to_context(context, self.request)
        return context


RANKING_OPTIONS = {
    "countries-by-species": {
        "heading": "countries by number of ant species",
        "query": lambda n: list(
            AntSpecies.objects.filter(distribution__region__type="Country")
            .annotate(rank_entry_name=F("distribution__region__name"))
            .values("rank_entry_name")
            .annotate(total=Count("rank_entry_name"))
            .order_by("-total")[:n]
        ),
    },
    "countries-by-genera": {
        "heading": "countries by number of ant genera",
        "query": lambda n: list(
            AntSpecies.objects.filter(distribution__region__type="Country")
            .annotate(rank_entry_name=F("distribution__region__name"))
            .values("rank_entry_name")
            .annotate(total=Count("genus", distinct=True))
            .order_by("-total")[:n]
        ),
    },
    "species-by-countries": {
        "heading": "ant species by number of countries",
        "query": lambda n: list(
            AntSpecies.objects.filter(distribution__region__type="Country")
            .annotate(
                rank_entry_name=F("name"), total=Count("distribution__region__name")
            )
            .values("rank_entry_name", "total")
            .order_by("-total")[:n]
        ),
    },
    "genera-by-countries": {
        "heading": "ant genera by number of countries",
        "query": lambda n: list(
            AntSpecies.objects.filter(
                distribution__region__type="Country", genus__isnull=False
            )
            .values("genus__name")
            .annotate(
                rank_entry_name=F("genus__name"),
                total=Count("distribution__region__code", distinct=True),
            )
            .values("rank_entry_name", "total")
            .order_by("-total")[:n]
        ),
    },
    "genera-by-species": {
        "heading": "ant genera by number of species",
        "query": lambda n: list(
            Genus.objects.annotate(rank_entry_name=F("name"), total=Count("species"))
            .values("rank_entry_name", "total")
            .order_by("-total")[:n]
        ),
    },
    "authors-by-species": {
        "heading": "authors by number of ant species",
        "query": lambda n: list(
            AntSpecies.objects.annotate(rank_entry_name=F("author"))
            .values("rank_entry_name")
            .annotate(total=Count("rank_entry_name"))
            .order_by("-total")[:n]
        ),
    },
}


class TopListsHub(TemplateView):
    """Consolidated top lists page for the antdb section."""

    template_name = "ants/antdb/top_lists.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ranking_key = self.request.GET.get("ranking")
        entries_raw = self.request.GET.get("entries", "20")
        entries = int(entries_raw) if entries_raw in ("10", "20", "50") else 20
        context["ranking_options"] = RANKING_OPTIONS
        context["selected_ranking"] = ranking_key
        context["entries"] = entries
        if ranking_key in RANKING_OPTIONS:
            ranking = RANKING_OPTIONS[ranking_key]["query"](entries)
            context["ranking"] = ranking
            context["max_total"] = ranking[0]["total"] if ranking else 0
            context["heading"] = RANKING_OPTIONS[ranking_key]["heading"]
        return context


class ForbiddenInEUSpeciesListView(TemplateView):
    """View to list species that are forbidden to keep in the EU."""

    template_name = "ants/forbidden_in_eu_species_list.html"
    _FILENAME = "ant-species-forbidden-eu"

    def _get_queryset(self):
        return AntSpecies.objects.filter(forbidden_in_eu=True).order_by("name")

    def get(self, request, *args, **kwargs):
        export = request.GET.get("export")
        if export == "csv":
            qs = self._get_queryset()
            return export_csv_response(
                qs,
                self._FILENAME,
                headers=["Name"],
                row_getter=lambda item: [item.name],
            )
        if export == "json":
            data = list(self._get_queryset().values("id", "name", "slug"))
            return export_json_response(data, self._FILENAME)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        forbidden_species = self._get_queryset()
        is_print = self.request.GET.get("print") == "1"
        context["is_print"] = is_print

        total = forbidden_species.count()
        per_page = max(1, total) if is_print else 50
        paginator = Paginator(forbidden_species, per_page)
        page_number = None if is_print else self.request.GET.get("page")
        page_obj = paginator.get_page(page_number)

        context["page_obj"] = page_obj
        context["total_objects"] = total
        add_iframe_to_context(context, self.request)
        return context


class AntSpeciesDetail(DetailView):
    """Detail view of an ant species."""

    model = AntSpecies
    template_name = "ants/antspecies_detail/antspecies_detail.html"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("genus", "genus__tribe", "genus__tribe__sub_family")
            .prefetch_related(
                "commonname_set",
                "invalid_names",
                "sizes",
                "images",
                "speciesdescription_set",
            )
        )

    def __get_flight_frequency(self, ant_species):
        has_flights = Flight.objects.filter(ant_species=ant_species).exists()

        if has_flights:
            flight_frequency = Flight.objects.flight_frequency_per_month(ant_species)
            return json.dumps(
                [value for key, value in flight_frequency.items()],
                separators=(",", ":"),
            )

        return None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        ant = context["object"]

        countries = AntRegion.countries.filter(distribution__species=ant.id)

        context["countries"] = countries

        common_names = ant.common_names.all()
        context["common_names"] = common_names

        invalid_names = ant.invalid_names.all()
        context["invalid_names"] = invalid_names
        worker_size = AntSize.objects.by_ant_and_type(ant.id, AntSize.WORKER)
        queen_size = AntSize.objects.by_ant_and_type(ant.id, AntSize.QUEEN)
        male_size = AntSize.objects.by_ant_and_type(ant.id, AntSize.MALE)

        context["worker_size"] = worker_size
        context["queen_size"] = queen_size
        context["male_size"] = male_size
        context["flight_frequency"] = self.__get_flight_frequency(ant)

        ratings = ant.difficulty_ratings.all()
        difficulty_ctx = _build_difficulty_context(ratings)
        context.update(difficulty_ctx)
        context["user_difficulty_rating"] = (
            ratings.filter(user=self.request.user).first()
            if self.request.user.is_authenticated
            else None
        )

        context.update(_build_food_context(ant, self.request.user))

        public_colonies_qs = Colony.objects.filter(species=ant, is_public=True)
        context["community_colonies_count"] = public_colonies_qs.count()
        context["community_journal_entries_count"] = ColonyJournalEntry.objects.filter(
            colony__in=public_colonies_qs
        ).count()
        context["species_images"] = list(ant.images.all())
        context["descriptions"] = ant.speciesdescription_set.all()
        context["antmaps_species_name"] = ant.name.replace(" ", ".")

        return context


def _build_difficulty_context(ratings):
    """Return difficulty rating aggregate data for template context."""
    choices = SpeciesDifficultyRating.DIFFICULTY_CHOICES
    total = ratings.count()
    distribution = {
        level: ratings.filter(difficulty=level).count() for level, _ in choices
    }
    avg = ratings.aggregate(avg=Avg("difficulty"))["avg"]
    avg_rounded = round(avg, 1) if avg is not None else None

    if total > 0:
        dominant_level = max(distribution, key=distribution.get)
        dominant_label = dict(choices)[dominant_level]
    else:
        dominant_level = None
        dominant_label = None

    return {
        "difficulty_distribution": distribution,
        "difficulty_total": total,
        "difficulty_choices": choices,
        "difficulty_avg": avg_rounded,
        "dominant_difficulty_level": dominant_level,
        "dominant_difficulty_label": dominant_label,
    }


def _build_food_acceptance_item_context(species, food_item, user):
    """Vote tallies + this user's own vote for one (species, food_item) pair."""
    ratings = SpeciesFoodRating.objects.filter(species=species, food_item=food_item)
    agg = ratings.aggregate(
        up_count=Count("id", filter=Q(vote=SpeciesFoodRating.UP)),
        down_count=Count("id", filter=Q(vote=SpeciesFoodRating.DOWN)),
    )
    user_vote = ratings.filter(user=user).first() if user.is_authenticated else None
    return {
        "food_item": food_item,
        "species": species,
        "up_count": agg["up_count"] or 0,
        "down_count": agg["down_count"] or 0,
        "user_vote": user_vote,
    }


def _build_food_context(species, user):
    """Return food acceptance vote data grouped by category for template context."""
    food_items = list(FoodItem.objects.all())

    categories = {}
    for food_item in food_items:
        item_ctx = _build_food_acceptance_item_context(species, food_item, user)
        cat = food_item.category
        categories.setdefault(cat, {
            "category_key": cat,
            "category_label": dict(FoodItem.CATEGORY_CHOICES)[cat],
            "items": [],
        })["items"].append(item_ctx)

    ordered_keys = [key for key, _ in FoodItem.CATEGORY_CHOICES]
    food_by_category = [categories[k] for k in ordered_keys if k in categories]
    return {"food_by_category": food_by_category}


_FOOD_OVERVIEW_TOP_N = 10


def _build_food_overview_item_context(food_item, user):
    ratings_qs = (
        SpeciesFoodRating.objects
        .filter(food_item=food_item)
        .values("species_id", "species__name", "species__slug")
        .annotate(
            net_score=Sum("vote"),
            up_count=Count("id", filter=Q(vote=SpeciesFoodRating.UP)),
            down_count=Count("id", filter=Q(vote=SpeciesFoodRating.DOWN)),
        )
        .order_by("-net_score", "-up_count")
    )
    all_species = list(ratings_qs)

    user_votes = {}
    if user.is_authenticated:
        user_votes = dict(
            SpeciesFoodRating.objects.filter(food_item=food_item, user=user)
            .values_list("species_id", "vote")
        )
    for row in all_species:
        row["user_vote"] = user_votes.get(row["species_id"])
        total_v = row["up_count"] + row["down_count"]
        row["acceptance_pct"] = round(row["up_count"] / total_v * 100) if total_v > 0 else 0
        row["total_votes"] = total_v

    agg = food_item.species_ratings.aggregate(net=Sum("vote"), total=Count("id"))
    up_total = sum(r["up_count"] for r in all_species)
    down_total = sum(r["down_count"] for r in all_species)
    total_ratings = agg["total"] or 0
    acceptance_pct = round(up_total / (up_total + down_total) * 100) if (up_total + down_total) > 0 else None

    return {
        "food_item": food_item,
        "top_species": all_species[:_FOOD_OVERVIEW_TOP_N],
        "extra_count": max(0, len(all_species) - _FOOD_OVERVIEW_TOP_N),
        "total_species": len(all_species),
        "total_ratings": total_ratings,
        "overall_net_score": agg["net"] or 0,
        "acceptance_pct": acceptance_pct,
        "up_total": up_total,
        "down_total": down_total,
    }


def _toggle_food_vote(species, food_item, user, vote_value):
    """Upsert or remove the (species, food_item, user) vote.

    Clicking the direction the user already has active removes the vote
    (un-vote); clicking the other direction switches it; no existing vote
    creates one.
    """
    existing = SpeciesFoodRating.objects.filter(
        species=species, food_item=food_item, user=user
    ).first()
    if existing is None:
        SpeciesFoodRating.objects.create(
            species=species, food_item=food_item, user=user, vote=vote_value
        )
    elif existing.vote == vote_value:
        existing.delete()
    else:
        existing.vote = vote_value
        existing.save(update_fields=["vote", "updated_at"])


def _parse_vote(request):
    """Parse and validate `vote` from POST data. Returns (vote_value, error_response)."""
    try:
        vote_value = int(request.POST.get("vote", ""))
    except (ValueError, TypeError):
        return None, HttpResponse(status=400)
    if vote_value not in (SpeciesFoodRating.UP, SpeciesFoodRating.DOWN):
        return None, HttpResponse(status=400)
    return vote_value, None


class SubmitFoodOverviewVoteView(LoginRequiredMixin, View):
    """Toggle a vote for one (food_item, species) pair from the food-overview page."""

    def post(self, request):
        try:
            food_item = FoodItem.objects.get(pk=int(request.POST.get("food_item_id", "")))
            species = AntSpecies.objects.get(pk=int(request.POST.get("species_id", "")))
        except (ValueError, TypeError, FoodItem.DoesNotExist, AntSpecies.DoesNotExist):
            return HttpResponse(status=400)

        vote_value, error = _parse_vote(request)
        if error:
            return error

        _toggle_food_vote(species, food_item, request.user, vote_value)

        return render(
            request,
            "ants/food_overview_species_list.html",
            _build_food_overview_item_context(food_item, request.user),
        )


class SubmitSpeciesFoodVoteView(LoginRequiredMixin, View):
    """Toggle a vote for one food item from the species-detail page (species implicit)."""

    def post(self, request, slug, food_item_id):
        species = get_object_or_404(AntSpecies, slug=slug)
        food_item = get_object_or_404(FoodItem, pk=food_item_id)

        vote_value, error = _parse_vote(request)
        if error:
            return error

        _toggle_food_vote(species, food_item, request.user, vote_value)

        return render(
            request,
            "ants/antspecies_detail/antspecies_detail_food_ratings_item.html",
            _build_food_acceptance_item_context(species, food_item, request.user),
        )


def _build_food_overview_list_context(selected_category, user):
    """Return food_data for one category, grouped by food item, for the overview list partial."""
    food_items = FoodItem.objects.filter(category=selected_category)

    # Per (food_item, species): net score and up/down counts
    species_qs = (
        SpeciesFoodRating.objects
        .filter(food_item__category=selected_category)
        .values("food_item_id", "species_id", "species__name", "species__slug")
        .annotate(
            net_score=Sum("vote"),
            up_count=Count("id", filter=Q(vote=SpeciesFoodRating.UP)),
            down_count=Count("id", filter=Q(vote=SpeciesFoodRating.DOWN)),
        )
        .order_by("food_item_id", "-net_score", "-up_count")
    )
    # Per food_item: overall net score and total count
    overall_qs = (
        SpeciesFoodRating.objects
        .filter(food_item__category=selected_category)
        .values("food_item_id")
        .annotate(overall_net=Sum("vote"), total_ratings=Count("id"))
    )
    overall_by_food = {r["food_item_id"]: r for r in overall_qs}

    user_votes = {}
    if user.is_authenticated:
        user_votes = {
            (r["food_item_id"], r["species_id"]): r["vote"]
            for r in SpeciesFoodRating.objects.filter(
                food_item__category=selected_category, user=user
            ).values("food_item_id", "species_id", "vote")
        }

    ratings_by_food = {}
    for row in species_qs:
        row["user_vote"] = user_votes.get((row["food_item_id"], row["species_id"]))
        total_v = row["up_count"] + row["down_count"]
        row["acceptance_pct"] = round(row["up_count"] / total_v * 100) if total_v > 0 else 0
        row["total_votes"] = total_v
        ratings_by_food.setdefault(row["food_item_id"], []).append(row)

    food_data = []
    for food_item in food_items:
        all_species = ratings_by_food.get(food_item.pk, [])
        ov = overall_by_food.get(food_item.pk, {})
        up_total = sum(r["up_count"] for r in all_species)
        down_total = sum(r["down_count"] for r in all_species)
        total_ratings = ov.get("total_ratings", 0)
        acceptance_pct = round(up_total / (up_total + down_total) * 100) if (up_total + down_total) > 0 else None

        food_data.append({
            "food_item": food_item,
            "top_species": all_species[:_FOOD_OVERVIEW_TOP_N],
            "extra_count": max(0, len(all_species) - _FOOD_OVERVIEW_TOP_N),
            "total_species": len(all_species),
            "total_ratings": total_ratings,
            "overall_net_score": ov.get("overall_net", 0) or 0,
            "acceptance_pct": acceptance_pct,
            "up_total": up_total,
            "down_total": down_total,
        })

    return {"food_data": food_data}


@method_decorator(never_cache, name="dispatch")
class FoodOverviewView(TemplateView):
    template_name = "ants/food_overview.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        valid_keys = [key for key, _ in FoodItem.CATEGORY_CHOICES]
        raw = self.request.GET.get("category", "")
        selected = raw if raw in valid_keys else valid_keys[0]

        category_counts = dict(
            FoodItem.objects.values("category")
            .annotate(count=Count("id"))
            .values_list("category", "count")
        )
        context["categories"] = FoodItem.CATEGORY_CHOICES
        context["category_counts"] = category_counts
        context["selected_category"] = selected
        context["selected_category_label"] = dict(FoodItem.CATEGORY_CHOICES)[selected]
        context.update(_build_food_overview_list_context(selected, self.request.user))
        return context


class FoodOverviewNewItemFormView(LoginRequiredMixin, View):
    """HTMX endpoint: returns the 'add new food item' form, pre-filled with a category."""

    def get(self, request):
        valid_keys = [key for key, _ in FoodItem.CATEGORY_CHOICES]
        category = request.GET.get("category", "")
        if category not in valid_keys:
            return HttpResponse(status=400)
        return render(
            request,
            "ants/food_overview_new_item_form.html",
            {
                "form": FoodItemCreateForm(initial={"category": category}),
                "category": category,
                "category_label": dict(FoodItem.CATEGORY_CHOICES)[category],
            },
        )


class FoodOverviewCreateItemView(LoginRequiredMixin, View):
    """HTMX endpoint: creates a new FoodItem suggested by a logged-in user."""

    MAX_CREATIONS_PER_WINDOW = 5
    RATE_LIMIT_WINDOW = datetime.timedelta(hours=1)

    def post(self, request):
        valid_keys = [key for key, _ in FoodItem.CATEGORY_CHOICES]
        category = request.POST.get("category", "")
        form = FoodItemCreateForm(request.POST, request.FILES)

        recent_count = FoodItem.objects.filter(
            created_by=request.user,
            created_at__gte=timezone.now() - self.RATE_LIMIT_WINDOW,
        ).count()
        if recent_count >= self.MAX_CREATIONS_PER_WINDOW:
            form.add_error(
                None,
                "You've added several food items recently. Please wait a bit before adding more.",
            )
            return render(
                request,
                "ants/food_overview_new_item_form.html",
                {
                    "form": form,
                    "category": category,
                    "category_label": dict(FoodItem.CATEGORY_CHOICES).get(category, ""),
                },
            )

        if category not in valid_keys or not form.is_valid():
            if category not in valid_keys:
                form.add_error(None, "Please choose a valid category.")
            return render(
                request,
                "ants/food_overview_new_item_form.html",
                {
                    "form": form,
                    "category": category,
                    "category_label": dict(FoodItem.CATEGORY_CHOICES).get(category, ""),
                },
            )

        try:
            with transaction.atomic():
                item = form.save(commit=False)
                item.created_by = request.user
                item.save()
        except IntegrityError:
            form.add_error(
                "name",
                "This name was just taken by another submission. Please use a different name or rate the existing item.",
            )
            return render(
                request,
                "ants/food_overview_new_item_form.html",
                {
                    "form": form,
                    "category": category,
                    "category_label": dict(FoodItem.CATEGORY_CHOICES)[category],
                },
            )

        list_html = render_to_string(
            "ants/food_overview_list.html",
            _build_food_overview_list_context(category, request.user),
            request=request,
        )
        return HttpResponse(list_html)


def _build_food_item_species_ratings_context(food_item_id, species_slug):
    food_item = get_object_or_404(FoodItem, pk=food_item_id)
    species = get_object_or_404(AntSpecies, slug=species_slug)
    ratings = (
        SpeciesFoodRating.objects
        .filter(food_item=food_item, species=species)
        .select_related("user")
        .order_by("-created_at")
    )
    return {"food_item": food_item, "species": species, "ratings": ratings}


@method_decorator(never_cache, name="dispatch")
class FoodItemDetailView(DetailView):
    """Detailed view for a single FoodItem showing acceptance stats, genus popularity, and feeding guide."""

    model = FoodItem
    template_name = "ants/food_item_detail.html"
    context_object_name = "food_item"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        food_item = self.object

        species_ratings_qs = (
            SpeciesFoodRating.objects
            .filter(food_item=food_item)
            .values("species_id", "species__name", "species__slug", "species__genus__name")
            .annotate(
                net_score=Sum("vote"),
                up_count=Count("id", filter=Q(vote=SpeciesFoodRating.UP)),
                down_count=Count("id", filter=Q(vote=SpeciesFoodRating.DOWN)),
                total_count=Count("id"),
            )
            .order_by("-net_score", "-up_count")
        )
        species_ratings = list(species_ratings_qs)

        user_votes = {}
        if self.request.user.is_authenticated:
            user_votes = dict(
                SpeciesFoodRating.objects.filter(food_item=food_item, user=self.request.user)
                .values_list("species_id", "vote")
            )

        genus_stats = {}
        for r in species_ratings:
            r["user_vote"] = user_votes.get(r["species_id"])
            total_v = r["up_count"] + r["down_count"]
            r["acceptance_pct"] = round(r["up_count"] / total_v * 100) if total_v > 0 else 0

            genus_name = r["species__genus__name"] or _("Other")
            if genus_name not in genus_stats:
                genus_stats[genus_name] = {
                    "genus": genus_name,
                    "species_count": 0,
                    "up_count": 0,
                    "down_count": 0,
                    "total_votes": 0,
                }
            genus_stats[genus_name]["species_count"] += 1
            genus_stats[genus_name]["up_count"] += r["up_count"]
            genus_stats[genus_name]["down_count"] += r["down_count"]
            genus_stats[genus_name]["total_votes"] += total_v

        genus_list = list(genus_stats.values())
        for g in genus_list:
            g["acceptance_pct"] = (
                round(g["up_count"] / g["total_votes"] * 100)
                if g["total_votes"] > 0
                else 0
            )
            g["net_score"] = g["up_count"] - g["down_count"]
        genus_list.sort(key=lambda x: (-x["acceptance_pct"], -x["total_votes"]))

        total_up = sum(r["up_count"] for r in species_ratings)
        total_down = sum(r["down_count"] for r in species_ratings)
        total_votes = total_up + total_down
        overall_acceptance = (
            round(total_up / total_votes * 100) if total_votes > 0 else None
        )
        overall_net = total_up - total_down

        context["species_ratings"] = species_ratings
        context["genus_list"] = genus_list
        context["total_up"] = total_up
        context["total_down"] = total_down
        context["total_votes"] = total_votes
        context["overall_acceptance"] = overall_acceptance
        context["overall_net"] = overall_net
        context["category_label"] = dict(FoodItem.CATEGORY_CHOICES).get(
            food_item.category, food_item.category
        )
        return context


@method_decorator(never_cache, name="dispatch")
class FoodItemSpeciesRatingsView(TemplateView):
    """Full list of individual ratings (with comment + rater) for one food item / species pair."""

    template_name = "ants/food_item_species_ratings.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            _build_food_item_species_ratings_context(kwargs["food_item_id"], kwargs["species_slug"])
        )
        return context


@method_decorator(never_cache, name="dispatch")
class FoodItemSpeciesRatingsListView(TemplateView):
    """HTMX fragment: just the vote-tally list for one food item / species pair."""

    template_name = "ants/food_item_species_ratings_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            _build_food_item_species_ratings_context(kwargs["food_item_id"], kwargs["species_slug"])
        )
        return context


@method_decorator(never_cache, name="dispatch")
class FoodOverviewSuggestSimilarView(LoginRequiredMixin, View):
    """HTMX endpoint: returns existing FoodItems whose name resembles the typed query."""

    MIN_QUERY_LENGTH = 3

    def get(self, request):
        name = request.GET.get("name", "").strip()
        if len(name) < self.MIN_QUERY_LENGTH:
            return HttpResponse("")
        matches = FoodItem.objects.filter(name__icontains=name).order_by("name")[:10]
        return render(request, "ants/food_overview_suggest.html", {"matches": matches})


class SubmitDifficultyRatingView(LoginRequiredMixin, View):
    """Accept a difficulty rating POST for an ant species and return the updated partial."""

    def post(self, request, slug):
        species = AntSpecies.objects.get(slug=slug)
        try:
            difficulty = int(request.POST.get("difficulty", ""))
        except (ValueError, TypeError):
            return HttpResponse(status=400)

        valid_levels = [level for level, _ in SpeciesDifficultyRating.DIFFICULTY_CHOICES]
        if difficulty not in valid_levels:
            return HttpResponse(status=400)

        comment = request.POST.get("comment", "").strip()
        SpeciesDifficultyRating.objects.update_or_create(
            species=species,
            user=request.user,
            defaults={"difficulty": difficulty, "comment": comment},
        )

        ratings = species.difficulty_ratings.all()
        context = _build_difficulty_context(ratings)
        context.update({
            "object": species,
            "user_difficulty_rating": ratings.filter(user=request.user).first(),
        })
        return render(
            request,
            "ants/antspecies_detail/antspecies_detail_difficulty_rating.html",
            context,
        )


class AntSpeciesAutocomplete(autocomplete.Select2QuerySetView):
    """QuerySetView for flight habitat autocomplete."""

    def get_queryset(self):
        qs = AntSpecies.objects.filter(name__icontains=self.q)
        return qs


class NuptialFlightReportView(FormView):
    """Handles POST submissions of the nuptial flight report form (HTMX partial responses)."""

    form_class = NuptialFlightReportForm
    http_method_names = ["post"]

    def form_invalid(self, form):
        # Recover display name so the text input stays populated on re-render
        species_name = ""
        raw_id = form.data.get("ant_species")
        if raw_id:
            try:
                species_name = AntSpecies.objects.get(pk=int(raw_id)).name
            except (AntSpecies.DoesNotExist, ValueError, TypeError):
                pass
        return render(
            self.request,
            "ants/nuptial_flight_report_form.html",
            {"form": form, "species_name": species_name},
        )

    def form_valid(self, form):
        # Honeypot check: silently discard bot submissions
        if form.cleaned_data.get("website"):
            response = HttpResponse("")
            response["HX-Trigger"] = "flightReportSuccess"
            return response

        species = form.cleaned_data["ant_species"]
        months = form.cleaned_data["months"]
        source = form.cleaned_data["source"]
        name = form.cleaned_data["name"]
        email = form.cleaned_data["email"]
        send_copy = form.cleaned_data["send_copy"]

        month_names = ", ".join(str(m) for m in months)
        email_body = (
            f"Nuptial flight data report from {name} <{email}>\n"
            f"{'=' * 60}\n\n"
            f"Ant Species  : {species}\n"
            f"Reported months: {month_names}\n\n"
            f"Source / Notes:\n{source}\n\n"
            f"{'=' * 60}\n"
            f"Reply to: {email}"
        )

        try:
            send_mail(
                subject=f"[Flight Report] {species}",
                message=email_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.CONTACT_RECIPIENT_EMAIL],
                fail_silently=False,
            )
        except Exception:
            logger.exception("Failed to send nuptial flight report email")
            form.add_error(
                None,
                "Sorry, there was an error sending your report. Please try again later.",
            )
            return render(
                self.request,
                "ants/nuptial_flight_report_form.html",
                {"form": form, "species_name": str(form.cleaned_data["ant_species"])},
            )

        if send_copy:
            copy_body = (
                f"This is a copy of your nuptial flight data report sent via antkeeping.info.\n\n"
                f"{'=' * 60}\n\n"
                f"Ant Species  : {species}\n"
                f"Reported months: {month_names}\n\n"
                f"Source / Notes:\n{source}\n\n"
                f"{'=' * 60}\n"
            )
            try:
                send_mail(
                    subject=f"[Copy] Flight Report – {species}",
                    message=copy_body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=False,
                )
            except Exception:
                logger.exception("Failed to send copy email to %s", email)

        response = HttpResponse("")
        response["HX-Trigger"] = "flightReportSuccess"
        return response


class NuptialFlightSpeciesSuggestView(View):
    """HTMX endpoint: returns an HTML list of ant species matching the search query."""

    MIN_QUERY_LENGTH = 4

    def get(self, request):
        q = request.GET.get("q", "").strip()
        if len(q) < self.MIN_QUERY_LENGTH:
            return HttpResponse("")
        species = AntSpecies.objects.filter(name__icontains=q, valid=True).order_by(
            "name"
        )
        return render(
            request,
            "ants/nuptial_flight_species_suggestions.html",
            {"species": species},
        )


def _species_filter_queryset(request):
    """Return a filtered AntSpecies queryset based on GET filter params."""
    from ants.filters import AntSpeciesFilter

    qs = (
        AntSpecies.objects.filter(valid=True)
        .select_related("genus__tribe__sub_family")
        .prefetch_related("images", "sizes", "difficulty_ratings")
        .order_by("name")
    )
    return AntSpeciesFilter(request.GET, queryset=qs).qs


class SpeciesFilterView(TemplateView):
    """Dedicated species browser: filter ant species by biological attributes."""

    template_name = "ants/species_filter.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["genera"] = Genus.objects.all().order_by("name")
        context["subfamilies"] = SubFamily.objects.all().order_by("name")
        context["regions"] = AntRegion.countries.filter(code__isnull=False).order_by("name")
        context["difficulty_choices"] = SpeciesDifficultyRating.DIFFICULTY_CHOICES
        context["hibernation_choices"] = AntSpecies.HIBERNATION_CHOICES
        context["nutrition_choices"] = AntSpecies.NUTRITION_CHOICES
        context["colony_choices"] = AntSpecies.COLONY_STRUCTURE_CHOICES
        context["founding_choices"] = AntSpecies.FOUNDING_CHOICES
        return context


class SpeciesFilterResultsView(View):
    """HTMX partial view: returns the filtered species list fragment."""

    RESULTS_PER_PAGE = 24

    def get(self, request):
        qs = _species_filter_queryset(request)
        paginator = Paginator(qs, self.RESULTS_PER_PAGE)
        page_obj = paginator.get_page(request.GET.get("page", 1))
        view_mode = request.GET.get("view", "card")
        if view_mode not in ("card", "list"):
            view_mode = "card"

        return render(
            request,
            "ants/species_filter_results.html",
            {
                "page_obj": page_obj,
                "count": paginator.count,
                "view_mode": view_mode,
            },
        )


class SizeComparisonView(TemplateView):
    """Ant size comparison page: visualise species at their real-world size."""

    template_name = "ants/size_comparison.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["regions"] = AntRegion.countries.filter(code__isnull=False).order_by("name")
        return context


class SizeComparisonResultsView(View):
    """HTMX partial view: returns the ant size comparison card fragment."""

    MAX_RESULTS = 200

    def get(self, request):
        ant_type = request.GET.get("ant_type", AntSize.WORKER)
        if ant_type not in (AntSize.WORKER, AntSize.QUEEN):
            ant_type = AntSize.WORKER

        size_field = request.GET.get("size_field", "average")
        if size_field not in ("minimum", "average", "maximum"):
            size_field = "average"

        sort_order = request.GET.get("sort_order", "asc")
        region = request.GET.get("region", "")

        size_q = Q(sizes__type=ant_type)
        qs = AntSpecies.objects.filter(valid=True).filter(size_q)

        if region:
            try:
                qs = qs.filter(distribution__region__pk=int(region))
            except ValueError:
                qs = qs.filter(distribution__region__code__iexact=region)

        if size_field == "minimum":
            qs = qs.annotate(display_size=Min("sizes__minimum", filter=size_q))
        elif size_field == "average":
            qs = qs.filter(sizes__maximum__isnull=False, sizes__type=ant_type)
            qs = qs.annotate(
                display_size=ExpressionWrapper(
                    (Min("sizes__minimum", filter=size_q) + Max("sizes__maximum", filter=size_q)) / 2.0,
                    output_field=FloatField(),
                )
            )
        else:
            qs = qs.filter(sizes__maximum__isnull=False, sizes__type=ant_type)
            qs = qs.annotate(display_size=Max("sizes__maximum", filter=size_q))

        qs = qs.filter(display_size__isnull=False)
        order_prefix = "-" if sort_order == "desc" else ""
        qs = qs.distinct().order_by(f"{order_prefix}display_size")

        total = qs.count()
        ants = list(qs[: self.MAX_RESULTS])

        return render(
            request,
            "ants/size_comparison_results.html",
            {
                "ants": ants,
                "total": total,
                "max_results": self.MAX_RESULTS,
            },
        )


def _save_title_image(request, colony):
    """Validate and attach an uploaded title photo to a colony, replacing any
    existing one. Returns a ValidationError if the upload wasn't a usable
    image, or None on success/no-op."""
    uploaded = request.FILES.get("title_image")
    if not uploaded:
        return None
    try:
        forms.ImageField(required=False).clean(uploaded)
    except ValidationError as exc:
        return exc
    ColonyImage.objects.update_or_create(colony=colony, defaults={"image_file": uploaded})
    return None


def _annotate_journal_entries(queryset, user):
    """Annotates journal entries with like counts, non-removed comment counts, and user_has_liked flag."""
    qs = queryset.annotate(
        likes_count=Count("likes", distinct=True),
        comments_count=Count(
            "comments",
            filter=Q(comments__is_removed=False),
            distinct=True,
        ),
    )
    if user.is_authenticated:
        qs = qs.annotate(
            user_has_liked=Exists(
                ColonyJournalEntryLike.objects.filter(
                    entry=OuterRef("pk"), user=user
                )
            )
        )
    return qs


def _build_colony_detail_context(colony, request):
    is_owner = request.user.is_authenticated and request.user == colony.user
    censuses = colony.censuses.all()
    latest_census = censuses.first()
    care_events = colony.care_events.select_related("food_item").all()

    care_summary = {}
    for cat, _label in ColonyCareEvent.CATEGORY_CHOICES:
        latest = care_events.filter(category=cat).first()
        if latest:
            care_summary[cat] = latest

    worker_censuses = list(
        colony.censuses.filter(workers__isnull=False).order_by("date", "id")
    )
    census_chart_data = None
    if len(worker_censuses) >= 2:
        census_chart_data = {
            "labels": [c.date.strftime("%d.%m.%Y") for c in worker_censuses],
            "workers": [c.workers for c in worker_censuses],
            "is_estimated": [bool(c.workers_is_estimated) for c in worker_censuses],
        }

    journal_sort = request.GET.get("journal_sort", "date").strip()
    if journal_sort == "created":
        journal_entries = colony.journal_entries.prefetch_related("images").order_by(
            "-created_at", "-date"
        )
    else:
        journal_entries = colony.journal_entries.prefetch_related("images").order_by(
            "-date", "-created_at"
        )
    journal_entries = _annotate_journal_entries(journal_entries, request.user)

    context = {
        "colony": colony,
        "is_owner": is_owner,
        "journal_entries": journal_entries,
        "journal_sort": journal_sort,
        "censuses": censuses,
        "latest_census": latest_census,
        "care_events": care_events,
        "care_summary": care_summary,
        "status_choices": Colony.STATUS_CHOICES,
        "care_categories": ColonyCareEvent.CATEGORY_CHOICES,
        "journal_event_types": ColonyJournalEntry.EVENT_TYPE_CHOICES,
        "journal_event_types_grouped": [
            (_("General & Routine"), [
                (ColonyJournalEntry.EVENT_GENERAL, _("General update")),
                (ColonyJournalEntry.EVENT_FEEDING, _("Feeding / Food trial")),
            ]),
            (_("Milestones & Development"), [
                (ColonyJournalEntry.EVENT_FOUNDING, _("Founding / First eggs")),
                (ColonyJournalEntry.EVENT_FIRST_WORKER, _("First worker (Nanitic)")),
                (ColonyJournalEntry.EVENT_NEST_MOVE, _("Nest move / New setup")),
                (ColonyJournalEntry.EVENT_ALATES, _("Alates")),
                (ColonyJournalEntry.EVENT_NUPTIAL_FLIGHT, _("Nuptial flight")),
            ]),
            (_("Seasonal / Hibernation"), [
                (ColonyJournalEntry.EVENT_HIBERNATION_START, _("Hibernation started")),
                (ColonyJournalEntry.EVENT_HIBERNATION_END, _("Hibernation ended")),
            ]),
            (_("Incidents & Problems"), [
                (ColonyJournalEntry.EVENT_ESCAPE, _("Escape")),
                (ColonyJournalEntry.EVENT_ISSUE, _("Issue (mold, mites, die-off)")),
                (ColonyJournalEntry.EVENT_QUEEN_DIED, _("Queen died")),
            ]),
        ],
        "census_chart_json": json.dumps(census_chart_data) if census_chart_data else None,
    }
    if is_owner:
        context["journal_form"] = ColonyJournalEntryForm()
        context["census_form"] = ColonyCensusForm()
        context["care_form"] = ColonyCareEventForm()
        context["food_items"] = FoodItem.objects.all().order_by("name")
    return context


@method_decorator(never_cache, name="dispatch")
class ColonyCreateView(LoginRequiredMixin, FormView):
    """Full-page form for creating a new colony."""

    form_class = ColonyForm
    template_name = "ants/colony_form.html"

    MAX_CREATIONS_PER_WINDOW = 5
    RATE_LIMIT_WINDOW = datetime.timedelta(hours=1)

    def get_initial(self):
        initial = super().get_initial()
        species_id = self.request.GET.get("species")
        if species_id:
            try:
                species = AntSpecies.objects.get(pk=int(species_id))
                initial["species"] = species.id
            except (AntSpecies.DoesNotExist, ValueError):
                pass
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_edit"] = False
        species_name = kwargs.get("species_name")
        if not species_name:
            species_id = self.request.GET.get("species")
            if species_id:
                try:
                    species = AntSpecies.objects.get(pk=int(species_id))
                    species_name = species.name
                except (AntSpecies.DoesNotExist, ValueError):
                    pass
        context.setdefault("species_name", species_name or "")
        return context

    def form_invalid(self, form):
        # Recover the display name so the search input stays populated on re-render
        species_name = ""
        raw_id = form.data.get("species")
        if raw_id:
            try:
                species_name = AntSpecies.objects.get(pk=int(raw_id)).name
            except (AntSpecies.DoesNotExist, ValueError, TypeError):
                pass
        return self.render_to_response(self.get_context_data(form=form, species_name=species_name))

    def form_valid(self, form):
        recent_count = Colony.objects.filter(
            user=self.request.user,
            created_at__gte=timezone.now() - self.RATE_LIMIT_WINDOW,
        ).count()
        if recent_count >= self.MAX_CREATIONS_PER_WINDOW:
            form.add_error(
                None,
                "You've added several colonies recently. Please wait a bit before adding more.",
            )
            return self.form_invalid(form)

        colony = form.save(commit=False)
        colony.user = self.request.user
        try:
            with transaction.atomic():
                colony.save()
                queens = form.cleaned_data.get("initial_queens")
                workers = form.cleaned_data.get("initial_workers")
                estimated = bool(form.cleaned_data.get("initial_estimated"))
                if queens is not None or workers is not None:
                    census_date = colony.found_date or colony.purchase_date or timezone.now().date()
                    ColonyCensus.objects.create(
                        colony=colony,
                        date=census_date,
                        queens=queens,
                        queens_is_estimated=estimated,
                        workers=workers,
                        workers_is_estimated=estimated,
                        note="Initial count upon adding colony",
                    )
        except IntegrityError:
            form.add_error("name", "You already have a colony with this name.")
            return self.form_invalid(form)

        image_error = _save_title_image(self.request, colony)
        if image_error:
            messages.warning(
                self.request, f"Colony saved, but the photo could not be used: {image_error.messages[0]}"
            )

        return redirect(colony.get_absolute_url())


@method_decorator(never_cache, name="dispatch")
class ColonyUpdateView(LoginRequiredMixin, FormView):
    """Full-page form for editing an existing colony. Species is immutable once set."""

    form_class = ColonyForm
    template_name = "ants/colony_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.colony = get_object_or_404(Colony, user=request.user, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.colony
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_edit"] = True
        context["colony"] = self.colony
        context.setdefault("species_name", self.colony.species.name)
        return context

    def form_valid(self, form):
        colony = form.save()
        image_error = _save_title_image(self.request, colony)
        if image_error:
            messages.warning(
                self.request, f"Colony saved, but the photo could not be used: {image_error.messages[0]}"
            )
        return redirect(colony.get_absolute_url())


class ColonyDeleteView(LoginRequiredMixin, View):
    """Permanently deletes a colony (with its journal entries, counts, care logs, and photos)."""

    def post(self, request, pk):
        colony = get_object_or_404(Colony, user=request.user, pk=pk)
        confirm_name = request.POST.get("confirm_colony_name", "").strip()
        if confirm_name != colony.name:
            messages.error(
                request,
                _("Colony name did not match. Deletion was cancelled."),
            )
            return redirect(colony.get_absolute_url())

        name = colony.name
        colony.delete()
        messages.success(
            request,
            _('"{name}" and all associated entries were permanently deleted.').format(name=name),
        )
        return redirect("user_profile")


class ColonyStatusUpdateView(LoginRequiredMixin, View):
    """Changes a colony's status (Active / Dead / Given away)."""

    def post(self, request, pk):
        colony = get_object_or_404(Colony, user=request.user, pk=pk)
        valid_statuses = [key for key, _ in Colony.STATUS_CHOICES]
        status = request.POST.get("status")
        if status not in valid_statuses:
            return HttpResponse(status=400)
        colony.status = status
        colony.save()
        return redirect(colony.get_absolute_url())


class ColonyVisibilityUpdateView(LoginRequiredMixin, View):
    """Toggles a colony's public visibility and found-location sharing.

    Colonies are public by default, so these checkboxes are an opt-OUT:
    checking them makes the colony/location private, not public.
    """

    def post(self, request, pk):
        colony = get_object_or_404(Colony, user=request.user, pk=pk)
        colony.is_public = "keep_private" not in request.POST
        colony.share_found_location = "hide_found_location" not in request.POST
        colony.save()
        return redirect(colony.get_absolute_url())


class ColonyJournalEntryCreateView(LoginRequiredMixin, View):
    """Adds a journal entry (with optional photos) to one of the user's colonies."""

    MAX_IMAGES_PER_ENTRY = 6

    def post(self, request, pk):
        colony = get_object_or_404(Colony, user=request.user, pk=pk)
        form = ColonyJournalEntryForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Please provide both a date and a note for the journal entry.")
            return redirect(colony.get_absolute_url())

        entry = form.save(commit=False)
        entry.colony = colony
        entry.save()
        _attach_journal_images(request, entry, start_index=0)
        return redirect(colony.get_absolute_url())


class ColonyJournalEntryUpdateView(LoginRequiredMixin, View):
    """Edits a journal entry's date/note, applies a client-side reorder/removal
    of its existing photos, and appends any newly uploaded ones.

    The existing-photos reordering happens entirely in the browser (drag to
    reorder, click to remove) and is only sent here -- as an ordered list of
    surviving image IDs -- when the whole form is submitted, so nothing is
    persisted just from rearranging thumbnails.
    """

    def post(self, request, pk, entry_pk):
        colony = get_object_or_404(Colony, user=request.user, pk=pk)
        entry = get_object_or_404(ColonyJournalEntry, pk=entry_pk, colony=colony)
        form = ColonyJournalEntryForm(request.POST, instance=entry)
        if not form.is_valid():
            messages.error(request, "Please provide both a date and a note for the journal entry.")
            return redirect(colony.get_absolute_url())

        form.save()

        existing_images = {image.pk: image for image in entry.images.all()}
        kept_ids = []
        for raw_id in request.POST.getlist("existing_image"):
            if raw_id.isdigit() and int(raw_id) in existing_images and int(raw_id) not in kept_ids:
                kept_ids.append(int(raw_id))

        for index, image_id in enumerate(kept_ids):
            image = existing_images[image_id]
            if image.ordering != index:
                image.ordering = index
                image.save(update_fields=["ordering"])

        for image_id, image in existing_images.items():
            if image_id not in kept_ids:
                image.delete()

        _attach_journal_images(request, entry, start_index=len(kept_ids))
        return redirect(colony.get_absolute_url())




class ColonyCensusCreateView(LoginRequiredMixin, View):
    """Adds a population and brood census to a colony."""

    def post(self, request, pk):
        colony = get_object_or_404(Colony, user=request.user, pk=pk)
        form = ColonyCensusForm(request.POST, request.FILES)
        if not form.is_valid():
            for field, errs in form.errors.items():
                for err in errs:
                    messages.error(
                        request,
                        f"{field}: {err}" if field != "__all__" else err,
                    )
            return redirect(colony.get_absolute_url())

        census = form.save(commit=False)
        census.colony = colony
        try:
            census.full_clean()
            census.save()
            messages.success(request, _("Census recorded successfully."))
        except ValidationError as e:
            messages.error(request, "; ".join(e.messages))
        return redirect(colony.get_absolute_url())


class ColonyCensusDeleteView(LoginRequiredMixin, View):
    """Deletes a census entry from one of the user's colonies."""

    def post(self, request, pk, census_pk):
        colony = get_object_or_404(Colony, user=request.user, pk=pk)
        census = get_object_or_404(ColonyCensus, pk=census_pk, colony=colony)
        if census.image_file:
            census.image_file.delete(save=False)
        census.delete()
        messages.success(request, _("Census entry deleted."))
        return redirect(colony.get_absolute_url())


class ColonyCareEventCreateView(LoginRequiredMixin, View):
    """Adds a maintenance or care event to a colony."""

    def post(self, request, pk):
        colony = get_object_or_404(Colony, user=request.user, pk=pk)
        form = ColonyCareEventForm(request.POST)
        if not form.is_valid():
            messages.error(request, _("Please provide a valid care category and date."))
            return redirect(colony.get_absolute_url())

        event = form.save(commit=False)
        event.colony = colony
        event.save()
        messages.success(request, _("Care action recorded."))
        return redirect(colony.get_absolute_url())


class ColonyCareEventDeleteView(LoginRequiredMixin, View):
    """Deletes a care event from one of the user's colonies."""

    def post(self, request, pk, event_pk):
        colony = get_object_or_404(Colony, user=request.user, pk=pk)
        event = get_object_or_404(ColonyCareEvent, pk=event_pk, colony=colony)
        event.delete()
        messages.success(request, _("Care event deleted."))
        return redirect(colony.get_absolute_url())


class ColonyJournalEntryDeleteView(LoginRequiredMixin, View):
    """Deletes a journal entry (and its photos) from one of the user's colonies."""

    def post(self, request, pk, entry_pk):
        colony = get_object_or_404(Colony, user=request.user, pk=pk)
        entry = get_object_or_404(ColonyJournalEntry, pk=entry_pk, colony=colony)
        entry.delete()
        return redirect(colony.get_absolute_url())


def _attach_journal_images(request, entry, start_index):
    image_field = forms.ImageField(required=False)
    skipped = 0
    uploads = request.FILES.getlist("images")[: ColonyJournalEntryCreateView.MAX_IMAGES_PER_ENTRY]
    for offset, uploaded in enumerate(uploads):
        try:
            image_field.clean(uploaded)
        except ValidationError:
            skipped += 1
            continue
        ColonyJournalEntryImage.objects.create(
            journal_entry=entry, image_file=uploaded, ordering=start_index + offset
        )
    if skipped:
        messages.warning(request, f"{skipped} photo(s) couldn't be used and were skipped.")


@method_decorator(never_cache, name="dispatch")
class ColonyDetailView(DetailView):
    """Colony detail page. Public if the colony is public, owner-only otherwise."""

    model = Colony
    template_name = "ants/colony_detail.html"
    context_object_name = "colony"

    def get_object(self, queryset=None):
        colony = get_object_or_404(
            Colony.objects.select_related("species", "user", "title_image"),
            user__username__iexact=self.kwargs["username"],
            slug=self.kwargs["slug"],
        )
        is_owner = self.request.user.is_authenticated and self.request.user == colony.user
        if not colony.is_visible_publicly and not is_owner:
            raise Http404
        return colony

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_build_colony_detail_context(self.object, self.request))
        return context


def _visible_colonies():
    return Colony.objects.filter(is_public=True, force_private_by_staff=False)


def _community_journal_queryset(request):
    """Journal entries from public (and not staff-hidden) colonies, newest first."""
    qs = (
        ColonyJournalEntry.objects.filter(
            colony__is_public=True, colony__force_private_by_staff=False
        )
        .select_related("colony", "colony__species", "colony__user")
        .prefetch_related("images")
    )
    qs = _annotate_journal_entries(qs, request.user)

    sort = request.GET.get("sort", "created").strip()
    if sort == "date":
        qs = qs.order_by("-date", "-created_at")
    else:
        qs = qs.order_by("-created_at", "-date")

    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(note__icontains=q)

    if request.GET.get("has_photos") == "1":
        qs = qs.filter(images__isnull=False).distinct()

    event_type = request.GET.get("event_type", "").strip()
    if event_type:
        qs = qs.filter(event_type=event_type)

    genus_slug = request.GET.get("genus", "")
    if genus_slug:
        qs = qs.filter(colony__species__genus__slug__iexact=genus_slug)

    species_slug = request.GET.get("species", "")
    if species_slug:
        qs = qs.filter(colony__species__slug__iexact=species_slug)

    username = request.GET.get("user", "")
    if username:
        qs = qs.filter(colony__user__username__iexact=username)

    return qs


@method_decorator(never_cache, name="dispatch")
class CommunityJournalView(TemplateView):
    """Public feed of journal entries across all public colonies, with filters."""

    template_name = "ants/community_journal.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        public_species_ids = _visible_colonies().values_list("species_id", flat=True).distinct()
        context["species_list"] = (
            AntSpecies.objects.filter(pk__in=public_species_ids).order_by("name")
        )
        context["genera"] = (
            Genus.objects.filter(pk__in=AntSpecies.objects.filter(pk__in=public_species_ids).values_list("genus_id", flat=True))
            .order_by("name")
        )
        context["usernames"] = (
            _visible_colonies().values_list("user__username", flat=True).distinct().order_by("user__username")
        )
        context["event_types"] = ColonyJournalEntry.EVENT_TYPE_CHOICES
        return context


@method_decorator(never_cache, name="dispatch")
class CommunityJournalResultsView(View):
    """HTMX partial: the filtered, paginated journal entry list."""

    RESULTS_PER_PAGE = 20

    def get(self, request):
        qs = _community_journal_queryset(request)
        paginator = Paginator(qs, self.RESULTS_PER_PAGE)
        page_obj = paginator.get_page(request.GET.get("page", 1))
        return render(
            request,
            "ants/community_journal_results.html",
            {"page_obj": page_obj, "count": paginator.count},
        )


@method_decorator(never_cache, name="dispatch")
class UserColoniesView(View):
    """Public list of colonies for a specific user (used in breadcrumbs / user colony feed)."""

    def get(self, request, username):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        target_user = get_object_or_404(User, username__iexact=username)
        is_owner = request.user.is_authenticated and request.user == target_user

        if is_owner or request.user.is_staff:
            colonies = target_user.colonies.all()
        else:
            colonies = target_user.colonies.filter(is_public=True, force_private_by_staff=False)

        colonies = colonies.select_related("species", "title_image").prefetch_related("censuses").order_by("-created_at")

        return render(
            request,
            "ants/user_colonies.html",
            {
                "target_user": target_user,
                "is_owner": is_owner,
                "colonies": colonies,
            },
        )


@method_decorator(never_cache, name="dispatch")
class ColonyJournalView(View):
    """Dedicated journal chronology view for a single colony."""

    RESULTS_PER_PAGE = 20

    def get(self, request, username, slug):
        colony = get_object_or_404(
            Colony.objects.select_related("species", "user", "title_image"),
            user__username__iexact=username,
            slug=slug,
        )
        is_owner = request.user.is_authenticated and request.user == colony.user
        if not colony.is_visible_publicly and not is_owner and not request.user.is_staff:
            raise Http404

        qs = colony.journal_entries.prefetch_related("images")
        qs = _annotate_journal_entries(qs, request.user)

        sort = request.GET.get("sort", "date").strip()
        if sort == "created":
            qs = qs.order_by("-created_at", "-date")
        else:
            qs = qs.order_by("-date", "-created_at")

        event_type = request.GET.get("event_type", "").strip()
        if event_type:
            qs = qs.filter(event_type=event_type)

        if request.GET.get("has_photos") == "1":
            qs = qs.filter(images__isnull=False).distinct()

        paginator = Paginator(qs, self.RESULTS_PER_PAGE)
        page_obj = paginator.get_page(request.GET.get("page", 1))

        return render(
            request,
            "ants/colony_journal.html",
            {
                "colony": colony,
                "is_owner": is_owner,
                "page_obj": page_obj,
                "total_entries": paginator.count,
                "event_types": ColonyJournalEntry.EVENT_TYPE_CHOICES,
                "sort": sort,
                "current_event_type": event_type,
                "has_photos": request.GET.get("has_photos") == "1",
            },
        )


@method_decorator(never_cache, name="dispatch")
class ColonyJournalEntryDetailView(View):
    """Detail view for a single journal entry with likes and comments."""

    def get(self, request, username, slug, pk):
        entry = get_object_or_404(
            ColonyJournalEntry.objects.select_related(
                "colony", "colony__species", "colony__user", "colony__title_image"
            ).prefetch_related("images"),
            pk=pk,
            colony__slug=slug,
            colony__user__username__iexact=username,
        )
        is_owner = request.user.is_authenticated and request.user == entry.colony.user
        if not entry.colony.is_visible_publicly and not is_owner and not request.user.is_staff:
            raise Http404

        likes_count = entry.likes.count()
        user_has_liked = (
            request.user.is_authenticated and entry.likes.filter(user=request.user).exists()
        )

        if request.user.is_staff:
            comments = entry.comments.select_related("user", "removed_by").order_by("created_at")
        else:
            comments = entry.comments.filter(is_removed=False).select_related("user").order_by("created_at")

        active_comments_count = entry.comments.filter(is_removed=False).count()
        comment_form = ColonyJournalCommentForm()

        return render(
            request,
            "ants/colony_journal_detail.html",
            {
                "entry": entry,
                "colony": entry.colony,
                "is_owner": is_owner,
                "likes_count": likes_count,
                "user_has_liked": user_has_liked,
                "comments": comments,
                "comments_count": active_comments_count,
                "comment_form": comment_form,
            },
        )


class ColonyJournalEntryShortRedirectView(View):
    """Short URL redirect: /colonies/journal/<pk>/ -> canonical colony journal entry detail."""

    def get(self, request, pk):
        entry = get_object_or_404(
            ColonyJournalEntry.objects.select_related("colony", "colony__user"),
            pk=pk,
        )
        return redirect(entry.get_absolute_url())


@method_decorator(ensure_csrf_cookie, name="dispatch")
@method_decorator(never_cache, name="dispatch")
class ColonyJournalEntryLikeToggleView(View):
    """HTMX endpoint to toggle a heart/like on a journal entry."""

    def post(self, request, pk):
        if not request.user.is_authenticated:
            return HttpResponse(status=401)

        entry = get_object_or_404(ColonyJournalEntry.objects.select_related("colony"), pk=pk)
        is_owner = request.user == entry.colony.user
        if not entry.colony.is_visible_publicly and not is_owner and not request.user.is_staff:
            raise Http404

        like = ColonyJournalEntryLike.objects.filter(entry=entry, user=request.user).first()
        if like:
            like.delete()
            user_has_liked = False
        else:
            ColonyJournalEntryLike.objects.create(entry=entry, user=request.user)
            user_has_liked = True

        likes_count = entry.likes.count()

        return render(
            request,
            "ants/snippets/journal_like_button.html",
            {
                "entry": entry,
                "likes_count": likes_count,
                "user_has_liked": user_has_liked,
            },
        )


@method_decorator(never_cache, name="dispatch")
class ColonyJournalCommentCreateView(View):
    """Endpoint (HTMX or standard POST) to post a new comment on a journal entry."""

    def post(self, request, pk):
        if not request.user.is_authenticated:
            return HttpResponse(status=401)

        entry = get_object_or_404(ColonyJournalEntry.objects.select_related("colony", "colony__user"), pk=pk)
        is_owner = request.user == entry.colony.user
        if not entry.colony.is_visible_publicly and not is_owner and not request.user.is_staff:
            raise Http404

        comment_text = request.POST.get("comment", "").strip()
        if not comment_text:
            return HttpResponse(status=400)
        if len(comment_text) > 1000:
            comment_text = comment_text[:1000]

        comment = ColonyJournalComment.objects.create(
            entry=entry,
            user=request.user,
            comment=comment_text,
        )

        if request.headers.get("HX-Request"):
            return render(
                request,
                "ants/snippets/journal_comment_item.html",
                {
                    "comment": comment,
                    "entry": entry,
                    "is_owner": is_owner,
                },
            )

        return redirect(entry.get_absolute_url() + f"#comment-{comment.pk}")


@method_decorator(never_cache, name="dispatch")
class ColonyJournalCommentModerateView(View):
    """Staff-only moderation endpoint to mark comments as removed (spam/inappropriate) or restore them."""

    def post(self, request, comment_pk):
        if not request.user.is_staff:
            return HttpResponseForbidden("Staff only")

        comment = get_object_or_404(
            ColonyJournalComment.objects.select_related("entry", "entry__colony", "user"),
            pk=comment_pk,
        )
        action = request.GET.get("action", request.POST.get("action", "remove"))
        reason = request.POST.get("reason", request.GET.get("reason", "Spam / Inappropriate")).strip()

        if action == "restore":
            comment.is_removed = False
            comment.removed_at = None
            comment.removed_by = None
            comment.removal_reason = ""
            comment.save()
        else:
            comment.is_removed = True
            comment.removed_at = timezone.now()
            comment.removed_by = request.user
            comment.removal_reason = reason or "Spam / Inappropriate"
            comment.save()

        if request.headers.get("HX-Request"):
            return render(
                request,
                "ants/snippets/journal_comment_item.html",
                {
                    "comment": comment,
                    "entry": comment.entry,
                    "is_owner": request.user == comment.entry.colony.user,
                },
            )

        return redirect(comment.entry.get_absolute_url() + f"#comment-{comment.pk}")


@method_decorator(never_cache, name="dispatch")
class ColonyJournalCommentDeleteView(View):
    """Hard delete for a comment by its author, colony owner, or staff."""

    def post(self, request, comment_pk):
        if not request.user.is_authenticated:
            return HttpResponse(status=401)

        comment = get_object_or_404(
            ColonyJournalComment.objects.select_related("entry", "entry__colony", "user"),
            pk=comment_pk,
        )
        is_comment_author = request.user == comment.user
        is_colony_owner = request.user == comment.entry.colony.user
        if not (is_comment_author or is_colony_owner or request.user.is_staff):
            return HttpResponseForbidden("Permission denied")

        entry_url = comment.entry.get_absolute_url()
        comment.delete()

        if request.headers.get("HX-Request"):
            return HttpResponse("")

        return redirect(entry_url + "#comments")
