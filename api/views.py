from django.db.models import Q, F, Subquery
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework import generics
from rest_framework.response import Response

from ants.models import AntSpecies, Distribution, AntRegion, Genus

from .serializers import RegionSerializer, RegionListSerializer, \
    AntsWithNuptialFlightsListSerializer, \
    AntSpeciesDetailSerializer, AntSpeciesNameSerializer, \
    GenusNameSerializer

from .schemas import AntsSchema, GeneraSchema, RegionsSchema


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
    schema = AntsSchema()

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


class AntSpeciesDetailView(APIView):
    """
        Return a specific ant species.
    """
    schema = AntsSchema()

    def get(self, request, ant_species):
        ant_species_qs = AntSpecies.objects
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


class RegionView(APIView):
    """
        Return a specific region.
    """
    schema = RegionsSchema()

    def get(self, request, region):
        regions = AntRegion.objects
        try:
            int(region)
            regions = regions.filter(pk=region)
        except ValueError:
            code_query = Q(code=region)
            slug_query = Q(slug=region)
            regions = regions.filter(code_query | slug_query)
        finally:
            region = get_object_or_404(regions)

        serializer = RegionSerializer(region, many=False)
        return Response(serializer.data)


class RegionsView(generics.ListAPIView):
    """
        Return a list of all existing regions.
    """
    schema = RegionsSchema()
    serializer_class = RegionListSerializer

    def get_queryset(self):
        regions = AntRegion.objects.all()
        with_ants = self.request.query_params.get('with-ants', None)
        with_flight_months = (self.request
                                  .query_params.get(
                                      'with-flight-months',
                                      None))
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


class AntsByRegionView(APIView):
    """
        Return a list of ants which occur in the specific region.
    """
    schema = RegionsSchema()

    def get(self, request, region):
        ant_species_name = self.request.query_params.get(
            'antSpeciesName', None)
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
        finally:
            ants = ants.values(
                'id',
                'name',
                native=F('distribution__native'),
                protected=F('distribution__protected'),
                red_list_status=F('distribution__red_list_status'))

            if len(ants) == 0:
                raise Http404

            return Response(ants)


def get_species_in_query(region_query):
    return Q(species__in=Subquery(Distribution
                                  .objects
                                  .filter(region_query)
                                  .values('species__pk')))


class AntsByRegionDiffView(APIView):
    """
        Return a list of ants which occur in the specific region
        but not in the second region.
    """
    schema = RegionsSchema()

    def get(self, request, region, region2):
        region_query = get_region_query(region)
        region2_query = get_region_query(region2)
        species_in_query = get_species_in_query(region2_query)

        ants = (Distribution
                .objects
                .filter(region_query)
                .exclude(species_in_query)
                .order_by('species__name')
                .values(species_name=F('species__name')))

        return Response(ants)


class AntsByRegionCommonView(APIView):
    """
        Return a list of ants which occur in both regions.
    """
    schema = RegionsSchema()

    def get(self, request, region, region2):
        region_query = get_region_query(region)
        region2_query = get_region_query(region2)
        species_in_query = get_species_in_query(region2_query)

        ants = (Distribution
                .objects
                .filter(region_query, species_in_query)
                .order_by('species__name')
                .values(species_name=F('species__name')))

        return Response(ants)


class AntsByGenusView(generics.ListAPIView):
    """
        Return a list of ant species of the specific genus.
    """
    serializer_class = AntSpeciesNameSerializer
    schema = GeneraSchema()

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
    schema = GeneraSchema()
    serializer_class = GenusNameSerializer
    queryset = Genus.objects.all()


class AntSpeciesListView(generics.ListAPIView):
    schema = AntsSchema()
    serializer_class = AntSpeciesNameSerializer
    queryset = AntSpecies.objects.all()
