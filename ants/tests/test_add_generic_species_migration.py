from django.apps import apps
from django.test import TestCase

from ants.models import AntSpecies, Genus
from ants.migration_operations import add_generic_species_for_each_genus


class AntSpeciesManagerTestCase(TestCase):
    def setUp(self):
        Genus.objects.get_or_create_with_name('Lasius')
        Genus.objects.get_or_create_with_name('Myrmica')
        AntSpecies.objects.get_or_create_with_name('Formica sp.')
        add_generic_species_for_each_genus(apps)

    def test_species_exist(self):
        self.assertTrue(AntSpecies.objects.name_exists('Lasius sp.'))
        self.assertTrue(AntSpecies.objects.name_exists('Myrmica sp.'))
        self.assertTrue(AntSpecies.objects.name_exists('Formica sp.'))

    def test_ordering(self):
        self.assertEqual(AntSpecies.objects.filter(ordering=0).count(), 3)
