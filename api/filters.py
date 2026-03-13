import django_filters

from ants.models import AntRegion, AntSpecies


class AntSpeciesFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(
        field_name="name",
        lookup_expr="icontains",
        label="Search species by name (case-insensitive substring match).",
    )
    region = django_filters.CharFilter(
        method="filter_by_region",
        label="Filter by region code (e.g. DE, de-by) or region ID.",
    )
    forbidden_in_eu = django_filters.BooleanFilter(
        label="Filter by EU import restriction status.",
    )

    class Meta:
        model = AntSpecies
        fields = ["forbidden_in_eu"]

    def filter_by_region(self, queryset, name, value):
        try:
            int(value)
            return queryset.filter(distribution__region__pk=value).distinct()
        except ValueError:
            return queryset.filter(
                distribution__region__code__iexact=value
            ).distinct()


class AntSizeFilter(django_filters.FilterSet):
    region = django_filters.CharFilter(
        method="filter_by_region",
        label="Filter by region code (e.g. DE, de-by) or region ID.",
    )
    genus = django_filters.CharFilter(
        method="filter_by_genus",
        label="Filter by genus name (case-insensitive) or genus ID.",
    )

    class Meta:
        model = AntSpecies
        fields = []

    def filter_by_region(self, queryset, name, value):
        try:
            int(value)
            return queryset.filter(distribution__region__pk=value).distinct()
        except ValueError:
            return queryset.filter(
                distribution__region__code__iexact=value
            ).distinct()

    def filter_by_genus(self, queryset, name, value):
        try:
            int(value)
            return queryset.filter(genus__pk=value)
        except ValueError:
            return queryset.filter(genus__name__iexact=value)


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
