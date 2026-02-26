from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.response import Response

from ants.models import AntRegion, AntSpecies

from .filters import AntRegionFilter, AntSpeciesFilter
from .pagination import StandardResultsSetPagination
from .serializers import (
    AntSpeciesDetailSerializer,
    AntSpeciesNameSerializer,
    AntsWithNuptialFlightsListSerializer,
    RegionListSerializer,
)

_EXPERIMENTAL_WARNING = (
    '299 - "This API version is experimental and subject to change without notice"'
)


class ExperimentalApiMixin:
    """WARNING: Experimental API – not stable yet, may change without notice."""

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Warning"] = _EXPERIMENTAL_WARNING
        return response


class AntSpeciesListView(ExperimentalApiMixin, generics.ListAPIView):
    serializer_class = AntSpeciesNameSerializer
    pagination_class = StandardResultsSetPagination
    queryset = AntSpecies.objects.select_related("genus").all()
    filterset_class = AntSpeciesFilter


class RegionListView(ExperimentalApiMixin, generics.ListAPIView):
    queryset = AntRegion.objects.all()
    serializer_class = RegionListSerializer
    filterset_class = AntRegionFilter
    pagination_class = StandardResultsSetPagination


class NuptialFlightMonths(ExperimentalApiMixin, generics.ListAPIView):
    serializer_class = AntsWithNuptialFlightsListSerializer
    pagination_class = StandardResultsSetPagination

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


class AntSpeciesDetailView(ExperimentalApiMixin, generics.GenericAPIView):
    def get(self, request, ant_species):
        ant_species_qs = AntSpecies.objects.select_related("genus").prefetch_related(
            "sizes", "images"
        )
        try:
            int(ant_species)
            ant_species_qs = ant_species_qs.filter(pk=ant_species)
        except ValueError:
            slug_query = Q(slug=ant_species)
            name_query = Q(name=ant_species)
            ant_species_qs = ant_species_qs.filter(name_query | slug_query)
        finally:
            ant_species_object = get_object_or_404(ant_species_qs)

        serializer = AntSpeciesDetailSerializer(ant_species_object, many=False)
        return Response(serializer.data)
