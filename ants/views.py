"""
Module for all models of ants app.
"""

import json

from dal import autocomplete
from django.core.paginator import Paginator
from django.db.models import Count, F
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.text import slugify
from django.views.generic.base import TemplateView
from django.views.generic.detail import DetailView

from flights.models import Flight

from .models import AntRegion, AntSize, AntSpecies, Genus, SubFamily, Tribe
from .utils.export import export_csv_response, export_json_response

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
    """View for the nuptial flight table (formerly 'Ant Mating Chart')."""

    template_name = "ants/nuptial_flight_table.html"


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


class Ranking(TemplateView):
    template_name = "ants/antdb/ranking.html"
    num_entries = 50

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["num_entries"] = self.num_entries
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


class TopCountriesByNumberOfAntSpecies(Ranking):
    """Shows top countries by number of ant species."""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ranking = (
            AntSpecies.objects.filter(distribution__region__type="Country")
            .annotate(rank_entry_name=F("distribution__region__name"))
            .values("rank_entry_name")
            .annotate(total=Count("rank_entry_name"))
            .order_by("-total")[: self.num_entries]
        )
        context["ranking"] = ranking
        context["max_total"] = ranking[0]["total"] if ranking else 0
        context["heading"] = "countries by number of ant species"
        return context


class TopCountriesByNumberOfAntGenera(Ranking):
    """Shows top countries by number of ant genera."""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ranking = (
            AntSpecies.objects.filter(distribution__region__type="Country")
            .annotate(rank_entry_name=F("distribution__region__name"))
            .values("rank_entry_name")
            .annotate(total=Count("genus", distinct=True))
            .order_by("-total")[: self.num_entries]
        )

        context["ranking"] = ranking
        context["max_total"] = ranking[0]["total"] if ranking else 0
        context["heading"] = "countries by number of ant genera"
        return context


class TopAntSpeciesByNumberOfCountries(Ranking):
    """Shows top ant species by number of countries."""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ranking = (
            AntSpecies.objects.filter(distribution__region__type="Country")
            .annotate(
                rank_entry_name=F("name"), total=Count("distribution__region__name")
            )
            .values("rank_entry_name", "total")
            .order_by("-total")[: self.num_entries]
        )
        context["ranking"] = ranking
        context["max_total"] = ranking[0]["total"] if ranking else 0
        context["heading"] = "ant species by number of countries"
        return context


class TopAntGeneraByNumberOfCountries(Ranking):
    """Shows top ant genera by number of countries."""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ranking = (
            AntSpecies.objects.filter(
                distribution__region__type="Country", genus__isnull=False
            )
            .values("genus__name")
            .annotate(
                rank_entry_name=F("genus__name"),
                total=Count("distribution__region__code", distinct=True),
            )
            .values("rank_entry_name", "total")
            .order_by("-total")[: self.num_entries]
        )

        context["ranking"] = ranking
        context["max_total"] = ranking[0]["total"] if ranking else 0
        context["heading"] = "ant genera by number of countries"
        return context


class TopAntGeneraByNumberOfSpecies(Ranking):
    """Shows top ant species by number of countries."""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ranking = (
            Genus.objects.annotate(rank_entry_name=F("name"), total=Count("species"))
            .values("rank_entry_name", "total")
            .order_by("-total")[: self.num_entries]
        )
        context["ranking"] = ranking
        context["max_total"] = ranking[0]["total"] if ranking else 0
        context["heading"] = "ant genera by number of species"
        return context


class TopAuthorsByNumberOfAntSpecies(Ranking):
    """Shows top countries by number of ant species."""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ranking = (
            AntSpecies.objects.annotate(rank_entry_name=F("author"))
            .values("rank_entry_name")
            .annotate(total=Count("rank_entry_name"))
            .order_by("-total")[: self.num_entries]
        )
        context["ranking"] = ranking
        context["max_total"] = ranking[0]["total"] if ranking else 0
        context["heading"] = "authors by number of ant species"
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
