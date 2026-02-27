from django.db.models import F, Q, Subquery
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.response import Response

from ants.models import AntRegion, AntSpecies, Distribution, Genus

from .filters import AntRegionFilter
from .serializers import (
    AntSizeListSerializer,
    AntSpeciesDetailSerializer,
    AntSpeciesNameSerializer,
    AntsWithNuptialFlightsListSerializer,
    GenusNameSerializer,
    RegionListSerializer,
    RegionSerializer,
)


def get_months_array(flight_months):
    all_flight_months = [0] * 12

    for month in flight_months:
        all_flight_months[month.id - 1] = 1

    return all_flight_months


class NuptialFlightMonths(generics.ListAPIView):
    """
    Return a list with all ant species with nuptial flight months,
    including these months.
    """

    serializer_class = AntsWithNuptialFlightsListSerializer

    def get_queryset(self):
        ants = AntSpecies.objects.prefetch_related("flight_months").filter(
            flight_months__isnull=False, valid=True
        )
        name = self.request.query_params.get("name", None)
        region = self.request.query_params.get("region", None)

        if name is not None and len(name) >= 3:
            ants = ants.filter(name__icontains=name)

        if region is not None:
            ants = ants.filter(distribution__region__pk=region)

        return ants.distinct()


class AntWorkerSizeListView(generics.ListAPIView):
    queryset = AntSpecies.objects.filter(sizes__type="WORKER").annotate(
        minimum=F("sizes__minimum"), maximum=F("sizes__maximum")
    )
    serializer_class = AntSizeListSerializer


class AntQueenSizeListView(generics.ListAPIView):
    queryset = AntSpecies.objects.filter(sizes__type="QUEEN").annotate(
        minimum=F("sizes__minimum"), maximum=F("sizes__maximum")
    )
    serializer_class = AntSizeListSerializer


class AntSpeciesDetailView(generics.GenericAPIView):
    """
    Return a specific ant species.
    """

    def get(self, request, ant_species):
        ant_species_qs = AntSpecies.objects.select_related(
            "genus", "genus__tribe", "genus__tribe__sub_family"
        ).prefetch_related(
            "commonname_set",
            "invalid_names",
            "distribution",
            "distribution__region",
            "images",
            "sizes",
        )
        try:
            int(ant_species)
            ant_species_qs = ant_species_qs.filter(pk=ant_species)
        except ValueError:
            slug_query = Q(slug=ant_species)
            name_query = Q(name=ant_species)
            ant_species_qs = ant_species_qs.filter(name_query | slug_query)
        ant_species_object = get_object_or_404(ant_species_qs)

        serializer = AntSpeciesDetailSerializer(ant_species_object, many=False)
        return Response(serializer.data)


class RegionDetailView(generics.RetrieveAPIView):
    """
    Return a specific region by ID, code, or slug.
    """

    queryset = AntRegion.objects.all()
    serializer_class = RegionSerializer
    lookup_url_kwarg = "region"

    def get_object(self):
        lookup_value = self.kwargs.get(self.lookup_url_kwarg)
        queryset = self.get_queryset()

        try:
            obj = queryset.get(pk=lookup_value)
        except (ValueError, AntRegion.DoesNotExist):
            obj = get_object_or_404(
                queryset, Q(code=lookup_value) | Q(slug=lookup_value)
            )

        return obj


class RegionListView(generics.ListAPIView):
    """
    Return a list of all existing regions with filtering capabilities.
    """

    queryset = AntRegion.objects.all()
    serializer_class = RegionListSerializer
    # The filter backend is often already globally set in settings.py,
    # but defining it here explicitly is also fine.
    filterset_class = AntRegionFilter


def get_region_query(region):
    region_query = None
    try:
        int(region)
        region_query = Q(region__pk=region)
    except ValueError:
        code_query = Q(region__code=region)
        slug_query = Q(region__slug__iexact=region)
        region_query = code_query | slug_query
    return region_query


class AntsByRegionView(generics.GenericAPIView):
    """
    Return a list of ants which occur in the specific region.
    """

    def get(self, request, region):
        ant_species_name = self.request.query_params.get("antSpeciesName", None)
        ants = AntSpecies.objects

        if ant_species_name is not None:
            ants = ants.search_by_name(ant_species_name)

        try:
            int(region)
            ants = ants.filter(distribution__region__pk=region)
        except ValueError:
            code_query = Q(distribution__region__code=region)
            slug_query = Q(distribution__region__slug=region)
            ants = ants.filter(code_query | slug_query)

        ants = ants.values(
            "id",
            "name",
            "forbidden_in_eu",
            native=F("distribution__native"),
            protected=F("distribution__protected"),
            red_list_status=F("distribution__red_list_status"),
        )

        if len(ants) == 0:
            raise Http404

        return Response(ants)


def get_species_in_query(region_query):
    return Q(
        species__in=Subquery(
            Distribution.objects.filter(region_query).values("species__pk")
        )
    )


class AntsByRegionDiffView(generics.GenericAPIView):
    """
    Return a list of ants which occur in the specific region
    but not in the second region.
    """

    def get(self, request, region, region2):
        region_query = get_region_query(region)
        region2_query = get_region_query(region2)
        species_in_query = get_species_in_query(region2_query)

        ants = (
            Distribution.objects.filter(region_query)
            .exclude(species_in_query)
            .order_by("species__name")
            .values(name=F("species__name"))
        )

        return Response(ants)


class AntsByRegionCommonView(generics.GenericAPIView):
    """
    Return a list of ants which occur in both regions.
    """

    def get(self, request, region, region2):
        region_query = get_region_query(region)
        region2_query = get_region_query(region2)
        species_in_query = get_species_in_query(region2_query)

        ants = (
            Distribution.objects.filter(region_query, species_in_query)
            .order_by("species__name")
            .values(name=F("species__name"))
        )

        return Response(ants)


class AntsByGenusView(generics.ListAPIView):
    """
    Return a list of ant species of the specific genus.
    """

    serializer_class = AntSpeciesNameSerializer

    def get_queryset(self):
        id = self.kwargs["id"]
        ants = AntSpecies.objects.all()
        ants = ants.filter(genus__pk=id)
        ants = ants.values("id", "name")
        return ants


class GeneraListView(generics.ListAPIView):
    """
    Return a list of genera.
    """

    serializer_class = GenusNameSerializer
    queryset = Genus.objects.all()


class AntSpeciesListView(generics.ListAPIView):
    """
    Return a (very long) list of all ant species. Please cache the list.
    """

    serializer_class = AntSpeciesNameSerializer
    queryset = AntSpecies.objects.all()
