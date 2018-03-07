from django.contrib import admin
from django.utils.translation import ugettext as _
from ants.models import AntSize, AntSpecies, CommonName, SpeciesDescription, \
    Family, Genus, ObsoleteName, SubFamily


class AntSizeInline(admin.StackedInline):
    model = AntSize
    extra = 0


class DescriptionInline(admin.StackedInline):
    model = SpeciesDescription
    extra = 0


class ObsoleteNameInline(admin.StackedInline):
    model = ObsoleteName
    extra = 0


class CommonNameInline(admin.StackedInline):
    model = CommonName
    extra = 0


class BaseAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(AntSpecies)
class AntSpeciesAdmin(BaseAdmin):
    filter_horizontal = ['flight_months', 'countries', 'regions']
    fieldsets = [
        (_('General'),          {'fields': ['name', 'genus',
                                            'colony_structure',
                                            'worker_polymorphism',
                                            'nutrition', 'flight_months']}),
        (_('Distribution'), {'fields': ['countries', 'regions']})
    ]
    search_fields = ['name']

    inlines = [
        DescriptionInline, AntSizeInline,
        ObsoleteNameInline, CommonNameInline]


@admin.register(Family)
class FamilyAdmin(BaseAdmin):
    pass


@admin.register(Genus)
class GenusAdmin(BaseAdmin):
    pass


@admin.register(SubFamily)
class SubFamily(BaseAdmin):
    pass
