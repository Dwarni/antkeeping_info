from django.contrib import admin
from django.utils.translation import ugettext as _
from ants.models import AntRegion, AntSize, AntSpecies, CommonName, \
    Distribution, SpeciesDescription, Family, Genus, InvalidName, SubFamily


class AntSizeInline(admin.StackedInline):
    model = AntSize
    extra = 0


class DescriptionInline(admin.StackedInline):
    model = SpeciesDescription
    extra = 0


class DistributionInline(admin.StackedInline):
    model = Distribution
    extra = 0


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
        (_('General'),          {'fields': ['name', 'genus',
                                            'colony_structure',
                                            'worker_polymorphism',
                                            'nutrition', 'flight_months']})
    ]
    search_fields = ['name']

    inlines = [
        DistributionInline,
        DescriptionInline, AntSizeInline,
        InvalidNameInline, CommonNameInline]


@admin.register(Family)
class FamilyAdmin(BaseAdmin):
    pass


@admin.register(Genus)
class GenusAdmin(BaseAdmin):
    pass


@admin.register(SubFamily)
class SubFamily(BaseAdmin):
    pass


@admin.register(AntRegion)
class RegionAdmin(BaseAdmin):
    pass
