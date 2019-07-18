from django.contrib import admin
from django.core.cache import caches
from django.utils.translation import ugettext as _
from sorl.thumbnail.admin import AdminImageMixin
from ants.models import AntRegion, AntSize, AntSpecies, \
     AntSpeciesDistribution, AntSpeciesImage, CommonName, \
     Distribution, SpeciesDescription, Family, Genus, \
     InvalidName, SubFamily
from regions.models import Region


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
        return qs.select_related('region')


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
    list_display = ('name',)
    search_fields = ['name']


@admin.register(AntSpecies)
class AntSpeciesAdmin(BaseAdmin):
    filter_horizontal = ['flight_months']
    fieldsets = [
        (_('General'), {'fields': ['name', 'genus',
                                   'information_complete',
                                   'colony_structure',
                                   'worker_polymorphism',
                                   'founding']}),
        (_('Nuptial flight'), {'fields': ['flight_months', 'flight_hour_range',
                                          'flight_climate']}),
        (_('Keeping parameters'), {'fields': [
            'nutrition', 'nest_temperature', 'nest_humidity',
            'outworld_temperature', 'outworld_humidity', 'hibernation'
        ]})
    ]

    inlines = [
        DescriptionInline, AntSpeciesImageInline, AntSizeInline,
        InvalidNameInline, CommonNameInline]

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        else:
            obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(AntSpeciesDistribution)
class AntSpeciesDistributionAdmin(BaseAdmin):
    search_fields = ['name']
    fields = ['name']
    readonly_fields = ['name']
    inlines = [DistributionInline]


@admin.register(Family)
class FamilyAdmin(BaseAdmin):
    pass


@admin.register(Genus)
class GenusAdmin(BaseAdmin):
    pass


@admin.register(SubFamily)
class SubFamilyAdmin(BaseAdmin):
    pass


@admin.register(AntRegion)
class RegionAdmin(BaseAdmin):
    search_fields = ['name', 'code', 'parent__name']
