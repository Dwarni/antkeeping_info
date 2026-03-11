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
from django.db.models import Count, F
from django.http import HttpResponse, HttpResponseNotAllowed
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.text import slugify
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.generic.base import TemplateView, View
from django.views.generic.detail import DetailView
from django.views.generic.edit import FormView

logger = logging.getLogger(__name__)

from flights.models import Flight

from .forms import NuptialFlightReportForm
from .models import AntRegion, AntSize, AntSpecies, Genus, SubFamily, Tribe
from .utils.export import export_csv_response, export_json_response

_MONTH_NAMES_SHORT = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]
_MONTH_NAMES_FULL = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]
# List of (month_number, short_name) tuples for templates
MONTHS = [(i + 1, name) for i, name in enumerate(_MONTH_NAMES_SHORT)]
MONTHS_FULL = [(i + 1, name) for i, name in enumerate(_MONTH_NAMES_FULL)]


def _nuptial_flight_queryset(request):
    """Return a filtered AntSpecies queryset based on GET params."""
    qs = (
        AntSpecies.objects
        .prefetch_related("flight_months")
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
        entries.append({
            "name": ant.name,
            "slug": ant.slug,
            "forbidden_in_eu": ant.forbidden_in_eu,
            "flight_months": flight_month_ids,
            "flight_hour_range_lower": hr.lower if hr else None,
            "flight_hour_range_upper": (hr.upper - 1) if hr else None,
            "flight_climate": ant.flight_climate,
            "antwiki_slug": ant.name.replace(" ", "_"),
        })
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
            AntRegion.countries
            .filter(distribution__species__flight_months__isnull=False)
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
                AntRegion.states
                .filter(
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
            html = render_to_string("ants/nuptial_flight_table_print.html", context, request=request)
            return HttpResponse(html, content_type="text/html")

        total = qs.count()
        paginator = Paginator(qs, self.ENTRIES_PER_PAGE)
        page_obj = paginator.get_page(request.GET.get("page", 1))
        entries = _build_entries(page_obj.object_list)
        html = render_to_string(
            "ants/nuptial_flight_table_rows.html",
            {"entries": entries, "page_obj": page_obj, "total": total, "months": MONTHS},
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
                AntRegion.states
                .filter(
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
            return [ant.name] + month_flags + [time_str, climate_map.get(ant.flight_climate, "")]

        filename = _build_export_filename(request)
        return export_csv_response(qs, filename, headers, row_getter)


class NuptialFlightJSONExportView(View):
    """Server-side JSON export with current filter params."""

    def get(self, request):
        qs = _nuptial_flight_queryset(request)
        data = []
        for ant in qs:
            hr = ant.flight_hour_range
            data.append({
                "id": ant.id,
                "name": ant.name,
                "flight_months": sorted(m.id for m in ant.flight_months.all()),
                "flight_hour_range": {"lower": hr.lower, "upper": hr.upper - 1} if hr else None,
                "flight_climate": ant.flight_climate,
                "forbidden_in_eu": ant.forbidden_in_eu,
            })
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

        return context


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
            form.add_error(None, "Sorry, there was an error sending your report. Please try again later.")
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
        species = (
            AntSpecies.objects
            .filter(name__icontains=q, valid=True)
            .order_by("name")
        )
        return render(
            request,
            "ants/nuptial_flight_species_suggestions.html",
            {"species": species},
        )


def _species_filter_queryset(request):
    """Return a filtered AntSpecies queryset based on GET filter params."""
    qs = AntSpecies.objects.filter(valid=True).order_by("name")

    genus = request.GET.get("genus", "")
    if genus:
        qs = qs.filter(genus__slug=genus)

    hibernation = request.GET.get("hibernation", "")
    if hibernation:
        qs = qs.filter(hibernation=hibernation)

    worker_polymorphism = request.GET.get("worker_polymorphism", "")
    if worker_polymorphism == "true":
        qs = qs.filter(worker_polymorphism=True)
    elif worker_polymorphism == "false":
        qs = qs.filter(worker_polymorphism=False)

    nutrition = request.GET.get("nutrition", "")
    if nutrition:
        qs = qs.filter(nutrition=nutrition)

    colony_structure = request.GET.get("colony_structure", "")
    if colony_structure:
        qs = qs.filter(colony_structure=colony_structure)

    founding = request.GET.get("founding", "")
    if founding:
        qs = qs.filter(founding=founding)

    size_min = request.GET.get("size_min", "")
    size_max = request.GET.get("size_max", "")
    if size_min or size_max:
        qs = qs.filter(sizes__type=AntSize.WORKER)
        if size_min:
            qs = qs.filter(sizes__minimum__gte=size_min)
        if size_max:
            qs = qs.filter(sizes__maximum__lte=size_max)

    return qs.distinct()


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
        return render(request, "ants/species_filter_results.html", {
            "page_obj": page_obj,
            "count": paginator.count,
        })
