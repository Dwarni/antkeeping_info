from django.contrib import admin
from django.core.cache import caches
from django.utils.translation import ugettext as _
from ants.models import AntRegion, AntSize, AntSpecies, CommonName, \
    Distribution, SpeciesDescription, Family, Genus, InvalidName, SubFamily
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


class BaseAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(AntSpecies)
class AntSpeciesAdmin(BaseAdmin):
    filter_horizontal = ['flight_months']
    fieldsets = [
        (_('General'), {'fields': ['name', 'genus',
                                   'colony_structure',
                                   'worker_polymorphism',
                                   'flight_months']}),
        (_('Keeping parameters'), {'fields': [
            'hibernation', 'nutrition'
        ]})
    ]
    search_fields = ['name']

    inlines = [
        DistributionInline,
        DescriptionInline, AntSizeInline,
        InvalidNameInline, CommonNameInline]

    def get_formsets_with_inlines(self, request, obj=None):
        for inline in self.get_inline_instances(request, obj):
            if isinstance(inline, DistributionInline):
                inline.cached_regions = [
                    (i.pk, str(i)) for i in Region.objects.all()
                ]
            yield inline.get_formset(request, obj), inline


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
