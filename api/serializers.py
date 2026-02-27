"""Serializer module for api app."""

import rest_framework.serializers as serializers
from drf_extra_fields.fields import IntegerRangeField

import ants.models as ant_models


class SubFamilySerializer(serializers.ModelSerializer):
    """Serializer for a sub family object."""

    class Meta:
        model = ant_models.SubFamily
        fields = ("id", "name")
        read_only_fields = fields


class GenusNameSerializer(serializers.ModelSerializer):
    """Serializer for a list of genera with only id and name."""

    class Meta:
        model = ant_models.Genus
        fields = ("id", "name")
        read_only_fields = fields


class GenusSerializer(serializers.ModelSerializer):
    """Serializer for a genus object."""

    sub_family = SubFamilySerializer(
        many=False, read_only=True, source="tribe.sub_family"
    )

    class Meta:
        model = ant_models.Genus
        fields = ("id", "name", "sub_family")
        read_only_fields = fields


class CommonNamesSerializer(serializers.ModelSerializer):
    """Serializer for a list of common names."""

    language = serializers.SerializerMethodField()

    def get_language(self, obj):
        return obj.get_language_display()

    class Meta:
        model = ant_models.CommonName
        fields = ("language", "name")
        read_only_fields = fields


class InvalidNamesSerializer(serializers.ModelSerializer):
    """Serializer for a list of invalid names."""

    class Meta:
        model = ant_models.InvalidName
        fields = ("name",)
        read_only_fields = fields


class RegionSerializer(serializers.ModelSerializer):
    """Serializer for a region."""

    class Meta:
        model = ant_models.AntRegion
        fields = ("id", "name", "slug", "type", "code", "parent")
        read_only_fields = fields


class RegionListSerializer(serializers.ModelSerializer):
    """Serializer for a list of regions."""

    class Meta:
        model = ant_models.AntRegion
        fields = ("id", "code", "name", "slug", "type")
        read_only_fields = fields


class DistributionForAntSerializer(serializers.ModelSerializer):
    """
    Serializer for a list of distribution object. This serializer
    should be used as part of a serialized ant objects, so all
    the ant specific fields aren't included.
    """

    region = RegionListSerializer(many=False, read_only=True)

    class Meta:
        model = ant_models.Distribution
        fields = ("region",)
        read_only_fields = fields


class AntSizeListSerializer(serializers.ModelSerializer):
    minimum = serializers.FloatField()
    maximum = serializers.FloatField()

    class Meta:
        model = ant_models.AntSpecies
        fields = ("id", "name", "minimum", "maximum")


class AntSizeSerializer(serializers.ModelSerializer):
    """Serializer for AntSize object."""

    minimum = serializers.FloatField()
    maximum = serializers.FloatField()

    class Meta:
        model = ant_models.AntSize
        fields = ("type", "minimum", "maximum")
        read_only_fields = fields


class AntSpeciesImageSerializer(serializers.ModelSerializer):
    """Serialiizer for AntSpeciesImage object."""

    class Meta:
        model = ant_models.AntSpeciesImage
        fields = ("image_file", "main_image")


class AntSpeciesDetailSerializer(serializers.ModelSerializer):
    """Serializer for details of a specific ant."""

    genus = GenusSerializer(many=False, read_only=True)
    common_names = CommonNamesSerializer(many=True, read_only=True)
    invalid_names = InvalidNamesSerializer(many=True, read_only=True)
    distribution = DistributionForAntSerializer(many=True, read_only=True)
    colony_structure = serializers.SerializerMethodField()
    founding = serializers.SerializerMethodField()
    flight_climate = serializers.SerializerMethodField()
    hibernation = serializers.SerializerMethodField()
    nutrition = serializers.SerializerMethodField()
    images = AntSpeciesImageSerializer(many=True, read_only=True)

    sizes = AntSizeSerializer(many=True, read_only=True)

    def get_colony_structure(self, obj):
        return obj.get_colony_structure_display()

    def get_flight_climate(self, obj):
        return obj.get_flight_climate_display()

    def get_founding(self, obj):
        return obj.get_founding_display()

    def get_hibernation(self, obj):
        return obj.get_hibernation_display()

    def get_nutrition(self, obj):
        return obj.get_nutrition_display()

    class Meta:
        model = ant_models.AntSpecies
        exclude = ("ordering", "created_by", "created_at", "updated_by", "updated_at")


class AntsWithNuptialFlightsListSerializer(serializers.ModelSerializer):
    """Serializer for a list of ants with nuptial flight months."""

    flight_hour_range = IntegerRangeField()

    class Meta:
        model = ant_models.AntSpecies
        fields = (
            "id",
            "name",
            "flight_months",
            "flight_climate",
            "flight_hour_range",
            "forbidden_in_eu",
        )
        read_only_fields = fields


class AntSpeciesNameSerializer(serializers.ModelSerializer):
    """Serializer for a list of ants with only id and name."""

    class Meta:
        model = ant_models.AntSpecies
        fields = ("id", "name")
        read_only_fields = fields
