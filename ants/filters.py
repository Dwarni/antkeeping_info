import django_filters
from django_filters import BooleanFilter, CharFilter, NumberFilter

from .models import AntSize, AntSpecies


class AntSpeciesFilter(django_filters.FilterSet):
    search = CharFilter(
        field_name="name",
        lookup_expr="icontains",
        label="Search species by name (case-insensitive substring match).",
    )
    region = CharFilter(
        method="filter_by_region",
        label="Filter by region code (e.g. de, de-by) or region ID.",
    )
    forbidden_in_eu = BooleanFilter(
        label="Filter by EU import restriction status.",
    )
    genus = CharFilter(
        method="filter_by_genus",
        label="Filter by genus slug (e.g. lasius), name (e.g. Lasius), or integer ID.",
    )
    hibernation = CharFilter(
        method="filter_hibernation",
        label=(
            "Filter by hibernation type. Values: "
            "no (no hibernation), "
            "short (end of november until end of february), "
            "long (end of september until end of march)."
        ),
    )
    worker_polymorphism = BooleanFilter(
        field_name="worker_polymorphism",
        label="Filter by worker polymorphism (true/false).",
    )
    nutrition = CharFilter(
        method="filter_nutrition",
        label=(
            "Filter by nutrition type. Values: "
            "leaves (leaves, grass and other vegetables), "
            "omnivorous (sugar water, honey, insects, meat, seeds, nuts etc.), "
            "seeds (mainly seeds and nuts, but also dead insects and sugar water), "
            "sugar_insects (insects, meat, sugar water, honey etc.)."
        ),
    )
    colony_structure = CharFilter(
        method="filter_colony_structure",
        label="Filter by colony structure (mono, poly, or olig).",
    )
    founding = CharFilter(
        method="filter_founding",
        label=(
            "Filter by founding type. Values: "
            "c (claustral — queen needs no food), "
            "sc (semi-claustral — queen needs to be fed), "
            "sp (social parasitic — queen needs host workers), "
            "spp (social parasitic — founding possible with host pupae)."
        ),
    )
    size_min = NumberFilter(
        method="filter_size_min",
        label="Minimum worker size (mm). Returns species whose worker size range covers this value.",
    )
    size_max = NumberFilter(
        method="filter_size_max",
        label="Maximum worker size (mm). Returns species whose worker size range covers this value.",
    )
    valid = BooleanFilter(
        method="filter_valid",
        label="Filter by species validity (default: true). Set to false to include synonym/invalid species.",
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
            # Support both slug (e.g. "lasius") and full name (e.g. "Lasius")
            return queryset.filter(genus__slug__iexact=value) | queryset.filter(
                genus__name__iexact=value
            )

    def filter_size_min(self, queryset, name, value):
        # Single filter() call so all conditions apply to the same related row,
        # avoiding Django's multi-valued relationship join issue.
        # Overlap: ant's minimum <= size_min AND ant's maximum >= size_min
        return queryset.filter(
            sizes__type=AntSize.WORKER,
            sizes__minimum__lte=value,
            sizes__maximum__gte=value,
        )

    def filter_size_max(self, queryset, name, value):
        # Overlap: ant's maximum >= size_max AND ant's minimum <= size_max
        return queryset.filter(
            sizes__type=AntSize.WORKER,
            sizes__maximum__gte=value,
            sizes__minimum__lte=value,
        )

    def filter_colony_structure(self, queryset, name, value):
        return queryset.filter(colony_structure=value.upper())

    def filter_founding(self, queryset, name, value):
        return queryset.filter(founding=value.lower())

    def filter_nutrition(self, queryset, name, value):
        return queryset.filter(nutrition=value.upper())

    def filter_hibernation(self, queryset, name, value):
        return queryset.filter(hibernation=value.upper())

    def filter_valid(self, queryset, name, value):
        return queryset.filter(valid=value)

    @property
    def qs(self):
        # Apply valid=True by default when the param is absent
        queryset = super().qs
        if "valid" not in self.data:
            queryset = queryset.filter(valid=True)
        return queryset
