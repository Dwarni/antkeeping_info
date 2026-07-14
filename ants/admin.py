from django.contrib import admin, messages
from django.db import transaction
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
    FoodRatingSubmission,
    Genus,
    InvalidName,
    RatingPhoto,
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


class FoodItemOriginFilter(admin.SimpleListFilter):
    title = _("origin")
    parameter_name = "origin"

    def lookups(self, request, model_admin):
        return [("staff", _("Original (staff)")), ("user", _("User-submitted"))]

    def queryset(self, request, queryset):
        if self.value() == "staff":
            return queryset.filter(created_by__isnull=True)
        if self.value() == "user":
            return queryset.filter(created_by__isnull=False)
        return queryset


@admin.register(FoodItem)
class FoodItemAdmin(AdminImageMixin, admin.ModelAdmin):
    list_display = ("name", "category", "ordering", "created_by", "created_at")
    list_filter = ("category", FoodItemOriginFilter)
    search_fields = ("name",)
    list_editable = ("ordering",)
    readonly_fields = ("created_by", "created_at")
    ordering = ("category", "ordering", "name")
    actions = ["merge_food_items"]

    @admin.action(description=_("Merge selected items into one (lowest pk survives)"))
    def merge_food_items(self, request, queryset):
        items = list(queryset.order_by("pk"))
        if len(items) < 2:
            self.message_user(
                request,
                _("Select at least two food items to merge."),
                level=messages.WARNING,
            )
            return

        survivor, *losers = items
        loser_ids = [item.pk for item in losers]

        with transaction.atomic():
            # Operate per loser *submission* (not per link row), since one
            # submission can cover several species and only some of them may
            # collide with an existing survivor-side rating -- a collision
            # "splits" the submission rather than moving it wholesale.
            for loser_sub in list(FoodRatingSubmission.objects.filter(food_item_id__in=loser_ids)):
                keep_species_ids = []
                for link in list(loser_sub.species_food_ratings.select_related("species")):
                    existing = (
                        SpeciesFoodRating.objects
                        .filter(species=link.species, food_item=survivor, user_id=loser_sub.user_id)
                        .select_related("submission")
                        .first()
                    )
                    if existing is None:
                        keep_species_ids.append(link.species_id)
                        continue

                    # Collision: keep the higher acceptance, tie-break on most recent update.
                    loser_wins = loser_sub.acceptance > existing.submission.acceptance or (
                        loser_sub.acceptance == existing.submission.acceptance
                        and loser_sub.updated_at >= existing.submission.updated_at
                    )
                    if loser_wins:
                        old_survivor_sub = existing.submission
                        existing.delete()
                        if not old_survivor_sub.species_food_ratings.exists():
                            old_survivor_sub.delete()
                        keep_species_ids.append(link.species_id)
                    else:
                        link.delete()

                if keep_species_ids:
                    loser_sub.food_item = survivor
                    loser_sub.save(update_fields=["food_item"])
                    loser_sub.species_food_ratings.update(food_item=survivor)
                else:
                    loser_sub.delete()

            FoodItem.objects.filter(pk__in=loser_ids).delete()

        self.message_user(
            request,
            _(
                "Merged %(n)d item(s) into '%(name)s' (lowest pk of the selection survives)."
            )
            % {"n": len(losers), "name": survivor.name},
        )


@admin.register(SpeciesFoodRating)
class SpeciesFoodRatingAdmin(admin.ModelAdmin):
    list_display = ("species", "food_item", "user", "submission_acceptance", "created_at")
    list_filter = ("submission__acceptance", "food_item__category")
    search_fields = ("species__name", "food_item__name", "user__username")
    readonly_fields = ("created_at", "updated_at")
    list_select_related = ("submission",)

    @admin.display(description=_("Acceptance"))
    def submission_acceptance(self, obj):
        return obj.submission.get_acceptance_display()


class RatingPhotoInline(AdminImageMixin, admin.TabularInline):
    model = RatingPhoto
    extra = 0


@admin.register(FoodRatingSubmission)
class FoodRatingSubmissionAdmin(admin.ModelAdmin):
    list_display = ("food_item", "user", "acceptance", "condition", "created_at")
    list_filter = ("acceptance", "condition", "food_item__category")
    search_fields = ("food_item__name", "user__username")
    readonly_fields = ("created_at", "updated_at")
    inlines = [RatingPhotoInline]
