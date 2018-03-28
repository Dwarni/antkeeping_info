from django.apps import apps
from django.db.models import Manager, QuerySet


class TaxonomicRankManager(Manager):
    def name_exists(self, name):
        """Checks if the Taxonomic Rank with the passed named exits."""
        return self.get_queryset().filter(name=name).exists()

    def get_by_name(self, name):
        return self.get_queryset().get(name=name)

    def get_or_create_with_name(self, name):
        return self.get_queryset().get_or_create(name=name)[0]


class GenusManager(TaxonomicRankManager):
    pass


class AntSpeciesManager(TaxonomicRankManager):
    def add_with_name(self, name):
        ant = self.get_queryset().create(name=name)
        genus_name = name.split(' ')[0]
        GenusModel = apps.get_model('ants', 'Genus')
        genus = GenusModel.objects.get_or_create_with_name(genus_name)
        ant.genus = genus
        ant.full_clean()
        ant.save()
        return ant

    def get_or_create_with_name(self, name):
        if self.name_exists(name):
            return self.get_by_name(name)
        else:
            return self.add_with_name(name)

    def by_country(self, code):
        return self.get_queryset() \
            .filter(distribution__region__type='Country') \
            .filter(distribution__region__code=code)

    def by_region(self, code):
        return self.get_queryset() \
            .filter(distribution__region__parent__type='Country') \
            .filter(distribution__region__code=code)


class AntSizeManager(Manager):
    def by_ant_and_type(self, ant_id, type):
        size = self.get_queryset() \
            .filter(ant_species__id=ant_id) \
            .filter(type=type) \
            .first()

        return size


class AntRegionManager(Manager):
    def with_ants(self):
        return self.get_queryset() \
            .filter(distribution__isnull=False) \
            .distinct()


class CountryAntRegionManager(AntRegionManager):
    def get_queryset(self):
        return super().get_queryset() \
            .filter(type='Country')


class StateAntRegionManager(AntRegionManager):
    def get_queryset(self):
        return super().get_queryset() \
            .filter(parent__type='Country')

    def with_ants_and_country(self, country_code):
        return self.with_ants().filter(parent__code=country_code)
