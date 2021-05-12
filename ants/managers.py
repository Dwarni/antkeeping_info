"""
    Module which stores all the mangers of ant app.
"""
from django.apps import apps
from django.db.models import Manager, Q
from django.db import transaction


class TaxonomicRankManager(Manager):
    """Manager for TaxonomicRankModel."""

    use_in_migrations = True

    def name_exists(self, name):
        """Checks if the Taxonomic Rank with the specific name exits."""
        return self.get_queryset().filter(name=name).exists()

    def get_by_name(self, name):
        """Returns the Raxonomic rank with the specific name."""
        return self.get_queryset().get(name=name)

    def get_or_create_with_name(self, name):
        """
            Gets or create a Taxonomic rank with name.
            If there is already a Taxonomic rank with the specific name,
            this rank will be returned, otherwise a new taxonomic rank is
            created using the passed name.
        """
        return self.get_queryset().get_or_create(name=name)[0]


class GenusManager(TaxonomicRankManager):
    """Manager for GenusModel"""

    def by_country_code(self, code):
        return self.get_queryset() \
            .filter(species__distribution__region__type='Country') \
            .filter(species__distribution__region__code=code) \
            .distinct()


class AntSpeciesManager(TaxonomicRankManager):
    """Manager for AntSpeciesModel."""

    @transaction.atomic
    def add_with_name(self, name, genus_model=None):
        """
            Adds an ant species with the specific name.
            The method will extract the genus name from the species name.
            After that it'll check if there is already a genus with that name
            in the database. If yes this genus is used, otherwise a new genus
            with that name is created and then used.
        """
        ant = self.get_queryset().create(name=name)
        genus_name = name.split(' ')[0]
        if genus_model is None:
            genus_model = apps.get_model('ants', 'Genus')
        genus = genus_model.objects.get_or_create_with_name(genus_name)
        ant.genus = genus
        ant.full_clean()
        ant.save()
        return ant

    def get_or_create_with_name(self, name, genus_model=None):
        """
            Returns an existing ant species or creates a new one with specific
            name.
            The method will also automatically assign a genus to the ant
            species and if needed, also create a new one first.
        """
        if self.name_exists(name):
            return self.get_by_name(name)
        else:
            return self.add_with_name(name, genus_model)

    def get_or_create_with_genus_or_species_id(self, genus_id, species_id):
        """
            Return an existing ant species or create a new one if only genus'
            id was provided.
        """
        if species_id:
            return self.get_queryset().get(pk=species_id)
        else:
            genus_model = apps.get_model('ants', 'Genus')
            genus = genus_model.objects.get(pk=genus_id)
            new_name = genus.name + ' sp.'
            return self.get_or_create_with_name(new_name)

    def by_country_code(self, code):
        """
            Returns a QuerySet which only contains ants of the country
            with the specific code.
        """
        return self.get_queryset() \
            .filter(distribution__region__type='Country') \
            .filter(distribution__region__code=code) \
            .distinct()

    def by_country_code_and_genus(self, code, genus):
        """
        Return a QuerySet which contains only ants which occur in the
        specific country and belog to the specific genus.
        """
        return self.get_queryset() \
            .filter(distribution__region__type='Country') \
            .filter(distribution__region__code=code) \
            .filter(genus__name=genus) \
            .distinct()

    def by_region_code(self, code):
        """
            Returns a QuerySet which only contains ants of the region
            with the specific code. Only regions which parent's type is
            'Country' are considered.
        """
        return self.get_queryset() \
            .filter(distribution__region__parent__type='Country') \
            .filter(distribution__region__code=code) \
            .distinct()

    def search_by_name(self, search_name):
        """
            Return a QuerySet which only contains ants that contain
            the search_name either in their name, invalid names or
            common names.
        """
        return self.get_queryset().filter(
            Q(name__icontains=search_name) |
            Q(commonname__name__icontains=search_name) |
            Q(invalid_names__name__icontains=search_name)
        ).exclude(name__endswith='sp.').distinct()


class AntSizeManager(Manager):
    """Manager for AntSizeModel"""

    def by_ant_and_type(self, ant_id, ant_type):
        """
            Returns ant size object with specific ant_id and ant_type.
        """
        size = self.get_queryset() \
            .filter(ant_species__id=ant_id) \
            .filter(type=ant_type) \
            .first()

        return size


class AntRegionManager(Manager):
    """Manager for AntRegionModel"""

    def with_ants(self):
        """Returns all regions in which ants live"""
        return self.get_queryset() \
            .filter(distribution__isnull=False) \
            .distinct()

    def get_by_name(self, name):
        """Return a region by name."""
        return self.get_queryset() \
            .get(Q(name=name) |
                 Q(official_name=name) |
                 Q(antwiki_name=name))

    def find_by_name(self, name):
        """Return a region by name."""
        return self.get_queryset() \
            .filter(Q(name=name) |
                    Q(official_name=name) |
                    Q(antwiki_name=name))


class CountryAntRegionManager(AntRegionManager):
    """
        Manager for AntRegionModel.
        This manager makes it easy to query for ant regions of type
        'country'.
    """

    def get_queryset(self):
        """
            Returns a query set which only contains AntRegions of type
            'country'.
        """
        return super().get_queryset() \
            .filter(type='Country')


class StateAntRegionManager(AntRegionManager):
    """
        Manager for AntRegionModel.
        This manager makes it easy to query for ant regions whose
        parent's type is 'Country'.
    """

    def get_queryset(self):
        """
            Returns a query set which only contains AntRegions whose
            parent's type is 'Country'.
        """
        return super().get_queryset() \
            .filter(parent__type='Country')

    def with_ants_and_country(self, country_code):
        """
            Returns all regions which contain ants, whose parent's type is
            'Country' and whose parent's code equals to country_code.
        """
        return self.with_ants().filter(parent__code=country_code)
