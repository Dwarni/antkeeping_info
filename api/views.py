from django.db.models import Q
from rest_framework.views import APIView
import coreapi
import coreschema
from rest_framework.schemas import AutoSchema
from rest_framework import generics
from rest_framework.response import Response

from ants.models import AntSpecies, AntRegion, Genus

from .serializers import RegionListSerializer, \
    AntsWithNuptialFlightsListSerializer, AntListSerializer, \
    AntSpeciesNameSerializer, GenusNameSerializer


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
    schema = AutoSchema(manual_fields=[
        coreapi.Field(
            "name",
            required=False,
            location="query",
            schema=coreschema.String(
                description='Filter ants by passed name'),
        ),
        coreapi.Field(
            "region",
            required=False,
            location="query",
            schema=coreschema.Number(
                description='Display only ants, which occur in that region')
        ),
    ])

    def get_queryset(self):
        ants = AntSpecies.objects.filter(
            flight_months__isnull=False)
        name = self.request.query_params.get('name', None)
        region = self.request.query_params.get('region', None)

        if name is not None and len(name) >= 3:
            ants = ants.filter(name__icontains=name)

        if region is not None:
            ants = ants.filter(distribution__region__pk=region)

        return ants.distinct()


class RegionsView(generics.ListAPIView):
    """
        Return a list of all existing regions.
    """
    serializer_class = RegionListSerializer
    schema = AutoSchema(manual_fields=[
        coreapi.Field(
            "with-ants",
            required=False,
            location="query",
            schema=coreschema.Boolean(
                description='Displays only regions with ant species in \
                    database.'),
        ),
        coreapi.Field(
            "with-flight-months",
            required=False,
            location="query",
            schema=coreschema.Boolean(
                description='Displays only regions with ant that have \
                    flight months in db'),
        ),
        coreapi.Field(
            "type",
            required=False,
            location="query",
            schema=coreschema.String(
                description='Display only regions of specific type.')
        ),
        coreapi.Field(
            "parent",
            required=False,
            location="query",
            schema=coreschema.Integer(
                description='Display only regions with \
                    specific parent region.'),
        ),
    ]
    )

    def get_queryset(self):
        regions = AntRegion.objects.all()
        with_ants = self.request.query_params.get('with-ants', None)
        with_flight_months = self.request.query_params.get('with-flight-months', None)
        region_type = self.request.query_params.get('type', None)
        parent = self.request.query_params.get('parent', None)

        if with_ants is not None and with_ants.lower() == 'true':
            regions = regions.filter(distribution__isnull=False).distinct()

        if with_flight_months is not None and \
           with_flight_months.lower() == 'true':
            regions = regions = regions.filter(
                distribution__species__flight_months__isnull=False
            )

        if region_type:
            regions = regions.filter(type=region_type)

        if parent:
            regions = regions.filter(parent=parent)

        return regions.distinct()


class AntsByRegionView(APIView):
    """
        Return a list of ants which occur in the specific region.
    """
    # serializer_class = AntListSerializer
    schema = AutoSchema(manual_fields=[
        coreapi.Field(
            "region",
            required=True,
            location='path',
            schema=coreschema.String(
                description='ID, slug or code of a region.')
        )
    ])

    def get(self, request, region):
        ants = AntSpecies.objects

        try:
            int(region)
            ants = ants.filter(distribution__region__pk=region)
        except ValueError:
            code_query = Q(distribution__region__code=region)
            slug_query = Q(distribution__region__slug=region)
            ants = ants.filter(code_query | slug_query)
        finally:
            ants = ants.values(
                'id',
                'name',
                'distribution__native',
                'distribution__protected',
                'distribution__red_list_status')
            return Response(ants)


class AntsByGenusView(generics.ListAPIView):
    """
        Return a list of ant species of the specific genus.
    """
    serializer_class = AntSpeciesNameSerializer
    schema = AutoSchema(manual_fields=[
        coreapi.Field(
            "id",
            required=True,
            location='path',
            schema=coreschema.String(
                description='ID of genus')
        )
    ])

    def get_queryset(self):
        id = self.kwargs['id']
        ants = AntSpecies.objects.all()
        ants = ants.filter(genus__pk=id)
        ants = ants.values('id', 'name')
        return ants


class GeneraListView(generics.ListAPIView):
    """
        Return a list of genera.
    """
    serializer_class = GenusNameSerializer

    def get_queryset(self):
        return Genus.objects.all()
