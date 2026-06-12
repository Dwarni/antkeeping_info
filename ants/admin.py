from django.contrib import admin
from django.utils.translation import gettext as _
from sorl.thumbnail.admin import AdminImageMixin

from ants.models import (
    AntRegion,
    AntSize,
    AntSpecies,
    AntSpeciesDistribution,
    AntSpeciesImage,
    CommonName,
    Distribution,
    Family,
    FoodItem,
    Genus,
    InvalidName,
    SpeciesDifficultyRating,
    SpeciesFoodRating,
    SpeciesDescription,
    SubFamily,
    Tribe,
)


class AntSizeInline(admin.StackedInline):
    model = AntSize
    extra = 0


class DescriptionInline(admin.StackedInline):
    model = SpeciesDescription
    extra = 0


class DistributionInline(admin.StackedInline):
    model = Distribution
    extra = 0

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)
        if db_field.name == "region" and hasattr(self, "cached_regions"):
            field.choices = self.cached_regions
        return field

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("region")


class InvalidNameInline(admin.StackedInline):
    model = InvalidName
    extra = 0


class CommonNameInline(admin.StackedInline):
    model = CommonName
    extra = 0


class AntSpeciesImageInline(AdminImageMixin, admin.StackedInline):
    model = AntSpeciesImage
    extra = 0


class BaseAdmin(AdminImageMixin, admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ["name"]


@admin.register(AntSpecies)
class AntSpeciesAdmin(BaseAdmin):
    filter_horizontal = ["flight_months"]
    fieldsets = [
        (
            _("General"),
            {
                "fields": [
                    "name",
                    "valid",
                    "author",
                    "year",
                    "genus",
                    "group",
                    "information_complete",
                    "forbidden_in_eu",
                    "colony_structure",
                    "worker_polymorphism",
                    "founding",
                ]
            },
        ),
        (
            _("Nuptial flight"),
            {
                "fields": [
                    "flight_months",
                    "flight_hour_range",
                    "flight_climate",
                    "flight_data_source",
                ]
            },
        ),
        (
            _("Keeping parameters"),
            {
                "fields": [
                    "nutrition",
                    "nest_temperature",
                    "nest_humidity",
                    "outworld_temperature",
                    "outworld_humidity",
                    "hibernation",
                ]
            },
        ),
    ]

    inlines = [
        DescriptionInline,
        AntSpeciesImageInline,
        AntSizeInline,
        InvalidNameInline,
        CommonNameInline,
    ]

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        else:
            obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(AntSpeciesDistribution)
class AntSpeciesDistributionAdmin(BaseAdmin):
    search_fields = ["name"]
    fields = ["name"]
    readonly_fields = ["name"]
    inlines = [DistributionInline]


@admin.register(Family)
class FamilyAdmin(BaseAdmin):
    pass


@admin.register(Genus)
class GenusAdmin(BaseAdmin):
    list_filter = ("tribe",)


@admin.register(Tribe)
class TribeAdmin(BaseAdmin):
    pass


@admin.register(SubFamily)
class SubFamilyAdmin(BaseAdmin):
    pass


@admin.register(AntRegion)
class RegionAdmin(BaseAdmin):
    search_fields = ["name", "code", "parent__name"]


@admin.register(SpeciesDifficultyRating)
class SpeciesDifficultyRatingAdmin(admin.ModelAdmin):
    list_display = ("species", "user", "difficulty", "created_at")
    list_filter = ("difficulty",)
    search_fields = ("species__name", "user__username")
    readonly_fields = ("created_at", "updated_at")


@admin.register(FoodItem)
class FoodItemAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "ordering")
    list_filter = ("category",)
    search_fields = ("name",)
    list_editable = ("ordering",)
    ordering = ("category", "ordering", "name")


@admin.register(SpeciesFoodRating)
class SpeciesFoodRatingAdmin(admin.ModelAdmin):
    list_display = ("species", "food_item", "user", "acceptance", "created_at")
    list_filter = ("acceptance", "food_item__category")
    search_fields = ("species__name", "food_item__name", "user__username")
    readonly_fields = ("created_at", "updated_at")
