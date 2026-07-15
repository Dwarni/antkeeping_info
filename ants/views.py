"""
Module for all models of ants app.
"""

import datetime
import json
import logging

from dal import autocomplete
from django.conf import settings
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Avg, Case, Count, ExpressionWrapper, F, FloatField, IntegerField, Max, Min, Q, Sum, When
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.text import slugify
from django.views.decorators.cache import never_cache
from django.views.generic.base import TemplateView, View
from django.views.generic.detail import DetailView
from django.views.generic.edit import FormView
from django.contrib.auth.mixins import LoginRequiredMixin

logger = logging.getLogger(__name__)

from flights.models import Flight

from .forms import FoodItemCreateForm, FoodRatingImageForm, NuptialFlightReportForm
from .models import AntRegion, AntSize, AntSpecies, FoodItem, FoodRatingSubmission, Genus, RatingPhoto, SpeciesDifficultyRating, SpeciesFoodRating, SubFamily, Tribe
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
        html = render_to_string(
            "ants/nuptial_flight_table_rows.html",
            {
                "entries": entries,
                "page_obj": page_obj,
                "total": total,
                "months": MONTHS,
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
            .prefetch_related("commonname_set", "invalid_names", "sizes", "images")
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


def _build_food_context(species, user):
    """Return food acceptance rating data grouped by category for template context."""
    food_items = list(FoodItem.objects.all())
    ratings_qs = species.food_ratings.select_related("food_item", "submission").all()

    ratings_by_food = {}
    user_rating_by_food = {}
    for rating in ratings_qs:
        fid = rating.food_item_id
        ratings_by_food.setdefault(fid, []).append(rating)
        if user.is_authenticated and rating.user_id == user.pk:
            user_rating_by_food[fid] = rating

    categories = {}
    for food_item in food_items:
        item_ratings = ratings_by_food.get(food_item.pk, [])
        total = len(item_ratings)
        avg = round(sum(r.submission.acceptance for r in item_ratings) / total, 1) if total > 0 else None

        cat = food_item.category
        if cat not in categories:
            categories[cat] = {
                "category_key": cat,
                "category_label": dict(FoodItem.CATEGORY_CHOICES)[cat],
                "items": [],
            }
        categories[cat]["items"].append({
            "food_item": food_item,
            "total": total,
            "avg": avg,
            "user_rating": user_rating_by_food.get(food_item.pk),
        })

    ordered_keys = [key for key, _ in FoodItem.CATEGORY_CHOICES]
    food_by_category = [categories[k] for k in ordered_keys if k in categories]
    return {"food_by_category": food_by_category}


_FOOD_OVERVIEW_TOP_N = 10


def _build_food_overview_item_context(food_item):
    ratings_qs = (
        SpeciesFoodRating.objects
        .filter(food_item=food_item)
        .values("species_id", "species__name", "species__slug")
        .annotate(species_avg=Avg("submission__acceptance"), rating_count=Count("id"))
        .order_by("-species_avg", "-rating_count")
    )
    all_species = list(ratings_qs)
    agg = food_item.species_ratings.aggregate(avg=Avg("submission__acceptance"), total=Count("id"))
    overall_avg = round(float(agg["avg"]), 1) if agg["avg"] is not None else None
    return {
        "food_item": food_item,
        "top_species": all_species[:_FOOD_OVERVIEW_TOP_N],
        "extra_count": max(0, len(all_species) - _FOOD_OVERVIEW_TOP_N),
        "total_species": len(all_species),
        "total_ratings": agg["total"],
        "overall_avg": overall_avg,
    }


def _parse_species_list(request, max_species):
    """Parse and validate the `species_id` list from POST data.

    Returns (species_list, error_response). On success error_response is None;
    on failure species_list is None and error_response is the response to return.
    """
    raw_species_ids = request.POST.getlist("species_id")
    if not raw_species_ids:
        return None, HttpResponse(status=400)
    try:
        species_ids = {int(v) for v in raw_species_ids}
    except (ValueError, TypeError):
        return None, HttpResponse(status=400)
    if len(species_ids) > max_species:
        return None, HttpResponse(status=400)
    species_list = list(AntSpecies.objects.filter(pk__in=species_ids))
    if len(species_list) != len(species_ids):
        return None, HttpResponse(status=400)
    return species_list, None


def _parse_acceptance_and_condition(request, food_item):
    """Parse and validate `acceptance`/`condition` from POST data for a food item.

    Returns (acceptance, condition, error_response).
    """
    try:
        acceptance = int(request.POST.get("acceptance", ""))
    except (ValueError, TypeError):
        return None, None, HttpResponse(status=400)
    valid_levels = [level for level, _ in FoodRatingSubmission.STAR_CHOICES]
    if acceptance not in valid_levels:
        return None, None, HttpResponse(status=400)
    required_conditions = FoodRatingSubmission.conditions_for_category(food_item.category)
    condition = request.POST.get("condition", "").strip() or None
    if required_conditions and condition not in required_conditions:
        return None, None, HttpResponse(status=400)
    condition = condition if required_conditions else None
    return acceptance, condition, None


def _parse_uploaded_images(request, max_count):
    """Validate uploaded `images` files. Returns (cleaned_images, error_response)."""
    uploads = request.FILES.getlist("images")
    if len(uploads) > max_count:
        return None, HttpResponse(status=400)
    cleaned_images = []
    for upload in uploads:
        image_form = FoodRatingImageForm(files={"image": upload})
        if not image_form.is_valid():
            return None, HttpResponse(status=400)
        cleaned_images.append(image_form.cleaned_data["image"])
    return cleaned_images, None


def _reassign_species_to_submission(species_list, food_item, user, submission):
    """Ensure each species' SpeciesFoodRating link points at `submission`.

    Returns the set of submission ids that lost a link and may now be orphaned.
    """
    orphan_candidates = set()
    for species in species_list:
        link, created = SpeciesFoodRating.objects.get_or_create(
            species=species,
            food_item=food_item,
            user=user,
            defaults={"submission": submission},
        )
        if not created and link.submission_id != submission.pk:
            orphan_candidates.add(link.submission_id)
            link.submission = submission
            link.save(update_fields=["submission", "updated_at"])
    return orphan_candidates


def _delete_orphaned_submissions(orphan_candidates):
    """Delete any FoodRatingSubmissions in `orphan_candidates` no longer referenced
    by a SpeciesFoodRating (cascades to their RatingPhotos)."""
    if not orphan_candidates:
        return
    still_referenced = set(
        SpeciesFoodRating.objects
        .filter(submission_id__in=orphan_candidates)
        .values_list("submission_id", flat=True)
    )
    FoodRatingSubmission.objects.filter(
        pk__in=orphan_candidates - still_referenced
    ).delete()


class SubmitFoodRatingFromOverviewView(LoginRequiredMixin, View):
    MAX_SPECIES_PER_SUBMISSION = 25
    MAX_PHOTOS_PER_SUBMISSION = 6

    def post(self, request):
        try:
            food_item = FoodItem.objects.get(pk=int(request.POST.get("food_item_id", "")))
        except (ValueError, TypeError, FoodItem.DoesNotExist):
            return HttpResponse(status=400)

        species_list, error = _parse_species_list(request, self.MAX_SPECIES_PER_SUBMISSION)
        if error:
            return error

        acceptance, condition, error = _parse_acceptance_and_condition(request, food_item)
        if error:
            return error

        cleaned_images, error = _parse_uploaded_images(request, self.MAX_PHOTOS_PER_SUBMISSION)
        if error:
            return error

        comment = request.POST.get("comment", "").strip()[:500]

        with transaction.atomic():
            submission = FoodRatingSubmission.objects.create(
                food_item=food_item,
                user=request.user,
                acceptance=acceptance,
                condition=condition,
                comment=comment,
            )
            for idx, image in enumerate(cleaned_images):
                RatingPhoto.objects.create(submission=submission, image=image, ordering=idx)

            orphan_candidates = _reassign_species_to_submission(
                species_list, food_item, request.user, submission
            )
            _delete_orphaned_submissions(orphan_candidates)

        return render(
            request,
            "ants/food_overview_species_list.html",
            _build_food_overview_item_context(food_item),
        )


def _build_food_rating_edit_context(submission):
    food_item = submission.food_item
    return {
        "submission": submission,
        "food_item": food_item,
        "current_species": [
            link.species for link in
            submission.species_food_ratings.select_related("species").all()
        ],
        "required_conditions": FoodRatingSubmission.conditions_for_category(food_item.category),
        "existing_photos": submission.photos.all(),
    }


class FoodRatingSubmissionEditView(LoginRequiredMixin, View):
    """Let the owner of a FoodRatingSubmission edit it in place (species list,
    acceptance, condition, comment, photos)."""

    MAX_SPECIES_PER_SUBMISSION = SubmitFoodRatingFromOverviewView.MAX_SPECIES_PER_SUBMISSION
    MAX_PHOTOS_PER_SUBMISSION = SubmitFoodRatingFromOverviewView.MAX_PHOTOS_PER_SUBMISSION

    def _get_owned_submission_or_none(self, request, pk):
        submission = get_object_or_404(FoodRatingSubmission, pk=pk)
        if submission.user_id != request.user.id:
            return None
        return submission

    def get(self, request, pk):
        submission = self._get_owned_submission_or_none(request, pk)
        if submission is None:
            return HttpResponseForbidden()
        return render(
            request,
            "ants/food_rating_edit_form.html",
            _build_food_rating_edit_context(submission),
        )

    def post(self, request, pk):
        submission = self._get_owned_submission_or_none(request, pk)
        if submission is None:
            return HttpResponseForbidden()
        food_item = submission.food_item

        species_list, error = _parse_species_list(request, self.MAX_SPECIES_PER_SUBMISSION)
        if error:
            return error

        acceptance, condition, error = _parse_acceptance_and_condition(request, food_item)
        if error:
            return error

        existing_photo_ids = set(submission.photos.values_list("pk", flat=True))
        try:
            remove_ids = {int(v) for v in request.POST.getlist("remove_photo_id")}
        except (ValueError, TypeError):
            return HttpResponse(status=400)
        if not remove_ids.issubset(existing_photo_ids):
            return HttpResponse(status=400)

        cleaned_images, error = _parse_uploaded_images(request, self.MAX_PHOTOS_PER_SUBMISSION)
        if error:
            return error

        remaining_existing = len(existing_photo_ids) - len(remove_ids)
        if remaining_existing + len(cleaned_images) > self.MAX_PHOTOS_PER_SUBMISSION:
            return HttpResponse(status=400)

        comment = request.POST.get("comment", "").strip()[:500]

        with transaction.atomic():
            submission.acceptance = acceptance
            submission.condition = condition
            submission.comment = comment
            submission.save(update_fields=["acceptance", "condition", "comment", "updated_at"])

            if remove_ids:
                RatingPhoto.objects.filter(submission=submission, pk__in=remove_ids).delete()
            if cleaned_images:
                next_ordering = RatingPhoto.objects.filter(submission=submission).aggregate(
                    Max("ordering")
                )["ordering__max"]
                next_ordering = 0 if next_ordering is None else next_ordering + 1
                for offset, image in enumerate(cleaned_images):
                    RatingPhoto.objects.create(
                        submission=submission, image=image, ordering=next_ordering + offset
                    )

            current_species_ids = set(
                submission.species_food_ratings.values_list("species_id", flat=True)
            )
            new_species_ids = {s.pk for s in species_list}
            removed_species_ids = current_species_ids - new_species_ids
            if removed_species_ids:
                SpeciesFoodRating.objects.filter(
                    submission=submission, species_id__in=removed_species_ids
                ).delete()

            orphan_candidates = _reassign_species_to_submission(
                species_list, food_item, request.user, submission
            )
            _delete_orphaned_submissions(orphan_candidates)

        response = HttpResponse("")
        response["HX-Trigger"] = "foodRatingEditSuccess"
        return response


def _build_food_overview_list_context(selected_category):
    """Return food_data for one category, grouped by food item, for the overview list partial."""
    food_items = FoodItem.objects.filter(category=selected_category)

    # Per (food_item, species): avg acceptance and rating count
    species_qs = (
        SpeciesFoodRating.objects
        .filter(food_item__category=selected_category)
        .values("food_item_id", "species_id", "species__name", "species__slug")
        .annotate(species_avg=Avg("submission__acceptance"), rating_count=Count("id"))
        .order_by("food_item_id", "-species_avg")
    )
    # Per food_item: overall avg and total count
    overall_qs = (
        SpeciesFoodRating.objects
        .filter(food_item__category=selected_category)
        .values("food_item_id")
        .annotate(overall_avg=Avg("submission__acceptance"), total_ratings=Count("id"))
    )
    overall_by_food = {r["food_item_id"]: r for r in overall_qs}

    ratings_by_food = {}
    for row in species_qs:
        ratings_by_food.setdefault(row["food_item_id"], []).append(row)

    food_data = []
    for food_item in food_items:
        all_species = ratings_by_food.get(food_item.pk, [])
        ov = overall_by_food.get(food_item.pk, {})
        ov_avg = ov.get("overall_avg")
        food_data.append({
            "food_item": food_item,
            "top_species": all_species[:_FOOD_OVERVIEW_TOP_N],
            "extra_count": max(0, len(all_species) - _FOOD_OVERVIEW_TOP_N),
            "total_species": len(all_species),
            "total_ratings": ov.get("total_ratings", 0),
            "overall_avg": round(float(ov_avg), 1) if ov_avg is not None else None,
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

        context["categories"] = FoodItem.CATEGORY_CHOICES
        context["selected_category"] = selected
        context["selected_category_label"] = dict(FoodItem.CATEGORY_CHOICES)[selected]
        context.update(_build_food_overview_list_context(selected))
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
            _build_food_overview_list_context(category),
            request=request,
        )
        return HttpResponse(list_html)


def _build_food_item_species_ratings_context(food_item_id, species_slug):
    food_item = get_object_or_404(FoodItem, pk=food_item_id)
    species = get_object_or_404(AntSpecies, slug=species_slug)
    ratings = (
        SpeciesFoodRating.objects
        .filter(food_item=food_item, species=species)
        .select_related("user", "submission")
        .prefetch_related("submission__photos")
        .order_by("-created_at")
    )
    return {"food_item": food_item, "species": species, "ratings": ratings}


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
    """HTMX fragment: just the ratings list, refreshed after a foodRatingEditSuccess event."""

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

    qs = AntSpecies.objects.filter(valid=True).order_by("name")
    return AntSpeciesFilter(request.GET, queryset=qs).qs


class SpeciesFilterView(TemplateView):
    """Dedicated species browser: filter ant species by biological attributes."""

    template_name = "ants/species_filter.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["genera"] = Genus.objects.all()
        context["hibernation_choices"] = AntSpecies.HIBERNATION_CHOICES
        context["nutrition_choices"] = AntSpecies.NUTRITION_CHOICES
        context["colony_choices"] = AntSpecies.COLONY_STRUCTURE_CHOICES
        context["founding_choices"] = AntSpecies.FOUNDING_CHOICES
        return context


class SpeciesFilterResultsView(View):
    """HTMX partial view: returns the filtered species list fragment."""

    RESULTS_PER_PAGE = 50

    def get(self, request):
        qs = _species_filter_queryset(request)
        paginator = Paginator(qs, self.RESULTS_PER_PAGE)
        page_obj = paginator.get_page(request.GET.get("page", 1))
        return render(
            request,
            "ants/species_filter_results.html",
            {
                "page_obj": page_obj,
                "count": paginator.count,
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
