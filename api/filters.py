import django_filters

from ants.models import AntRegion, AntSpecies


class AntSpeciesFilter(django_filters.FilterSet):
    class Meta:
        model = AntSpecies
        fields = ["forbidden_in_eu"]


class AntRegionFilter(django_filters.FilterSet):
    # Mapping query params to specific filter methods or fields
    with_ants = django_filters.BooleanFilter(method="filter_with_ants")
    with_flight_months = django_filters.BooleanFilter(
        method="filter_with_flight_months"
    )

    class Meta:
        model = AntRegion
        fields = ["type", "parent"]

    def filter_with_ants(self, queryset, name, value):
        if value is True:
            return queryset.filter(distribution__isnull=False).distinct()
        return queryset

    def filter_with_flight_months(self, queryset, name, value):
        if value is True:
            return queryset.filter(
                distribution__species__flight_months__isnull=False
            ).distinct()
        return queryset
