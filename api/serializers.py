"""Serializer module for api app."""
from rest_framework.serializers import ModelSerializer
from drf_extra_fields.fields import IntegerRangeField

from ants.models import AntSpecies, AntRegion, Genus


class AntsWithNuptialFlightsListSerializer(ModelSerializer):
    """Serializer for a list of ants with nuptial flight months."""
    class Meta:
        model = AntSpecies
        flight_hour_range = IntegerRangeField(source='flight_hour_range')
        fields = ('id', 'name', 'flight_months',
                  'flight_climate', 'flight_hour_range')
        read_only_fields = fields


class RegionListSerializer(ModelSerializer):
    """Serializer for a list of regions."""
    class Meta:
        model = AntRegion
        fields = ('id', 'name', 'slug', 'type')
        read_only_fields = fields


class AntListSerializer(ModelSerializer):
    """Serializer for a list of ants."""
    class Meta:
        model = AntSpecies
        fields = (
            'id', 'name', 'distribution__native', 'distribution__protected',
            'distribution__red_llist_status'
        )
        read_only_fields = fields


class AntSpeciesNameSerializer(ModelSerializer):
    """Serializer for a list of ants with only id and name."""
    class Meta:
        model = AntSpecies
        fields = (
            'id', 'name'
        )
        read_only_fields = fields


class GenusNameSerializer(ModelSerializer):
    """Serlializer for a list of genera with only id and name."""
    class Meta:
        model = Genus
        fields = (
            'id', 'name'
        )
        read_only_fields = fields
