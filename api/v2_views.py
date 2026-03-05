from django.db.models import Q
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
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


@extend_schema(
    parameters=[
        OpenApiParameter(
            "month",
            OpenApiTypes.INT,
            description="Filter by flight month ID. Returns only species that swarm in this month.",
        ),
        OpenApiParameter(
            "name",
            OpenApiTypes.STR,
            description="Filter by species name (case-insensitive, minimum 3 characters).",
        ),
        OpenApiParameter(
            "region",
            OpenApiTypes.INT,
            description="Filter by region ID. Returns only species distributed in this region.",
        ),
    ]
)
class NuptialFlightMonths(ExperimentalApiMixin, generics.ListAPIView):
    serializer_class = AntsWithNuptialFlightsListSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        ants = AntSpecies.objects.prefetch_related("flight_months").filter(
            flight_months__isnull=False, valid=True
        )
        name = self.request.query_params.get("name", None)
        region = self.request.query_params.get("region", None)
        month = self.request.query_params.get("month", None)

        if name is not None and len(name) >= 3:
            ants = ants.filter(name__icontains=name)

        if region is not None:
            ants = ants.filter(distribution__region__pk=region)

        if month is not None:
            ants = ants.filter(flight_months__id=month)

        return ants.distinct()


class AntSpeciesDetailView(ExperimentalApiMixin, generics.GenericAPIView):
    serializer_class = AntSpeciesDetailSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "ant_species",
                location=OpenApiParameter.PATH,
                description="Species identifier: integer ID, slug (e.g. lasius-niger), or scientific name (e.g. Lasius niger).",
            )
        ]
    )
    def get(self, request, ant_species):
        ant_species_qs = AntSpecies.objects.select_related("genus").prefetch_related(
            "sizes", "images"
        )
        try:
            int(ant_species)
            ant_species_qs = ant_species_qs.filter(pk=ant_species)
        except ValueError:
            ant_species_qs = ant_species_qs.filter(
                Q(slug=ant_species) | Q(name=ant_species)
            )
        ant_species_object = get_object_or_404(ant_species_qs)

        serializer = AntSpeciesDetailSerializer(ant_species_object, many=False)
        return Response(serializer.data)
