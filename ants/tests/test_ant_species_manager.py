from django.test import TestCase
from django.db.models import ObjectDoesNotExist
from django.db.utils import IntegrityError
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist, ValidationError

from ants.managers import AntSpeciesManager
from ants.models import AntSpecies, Genus
from regions.models import Country, Region


class AntSpeciesManagerTestCase(TestCase):
    manager = AntSpecies.objects
    test_name = 'Lasius testus'
    test_name_lower = test_name.lower()
    test_name_not_existant = 'Testus lasius'

    new_test_name = 'Lasiusios newus'
    new_test_name_genus = new_test_name.split(' ')[0]

    new_test_name2 = 'Lasius testicus'
    new_test_name2_genus = new_test_name2.split(' ')[0]

    def setUp(self):
        self.manager.create(name=self.test_name)

    def test_name_exists(self):
        self.assertTrue(self.manager.name_exists(self.test_name))
        self.assertFalse(self.manager.name_exists(self.test_name_lower))
        self.assertFalse(self.manager.name_exists(self.test_name_not_existant))

    def test_get_by_name(self):
        self.assertIsNotNone(self.manager.get_by_name(self.test_name))
        self.assertRaises(
            ObjectDoesNotExist,
            self.manager.get_by_name,
            name=self.test_name_lower
        )
        self.assertRaises(
            ObjectDoesNotExist,
            self.manager.get_by_name,
            name=self.test_name_not_existant
        )

    def test_add_with_name(self):
        with transaction.atomic():
            self.assertRaises(
                IntegrityError,
                self.manager.add_with_name,
                name=self.test_name
            )
        """Adding an existing name should rise an IntegrityError"""

        with transaction.atomic():
            self.assertRaises(
                ValidationError,
                self.manager.add_with_name,
                name='Lasius'
            )
        """Trying to add name 'Lasius' should raise a ValidationError"""

    def test_get_or_create_with_name(self):
        self.assertIsNotNone(
            self.manager.get_or_create_with_name(self.test_name)
        )

        new_ant = self.manager.get_or_create_with_name(self.new_test_name)
        self.assertIsNotNone(new_ant)
        """This should create a new object in the db and return it"""

        self.assertTrue(self.manager.name_exists(self.new_test_name))
        """Now check if a new species was created"""

        new_genus = Genus.objects.get_by_name(self.new_test_name_genus)
        self.assertEqual(new_genus.name, new_ant.genus.name)
        """Check if genus was created too and if both genus names are equal"""

        new_ant2 = self.manager.get_or_create_with_name(self.new_test_name2)
        self.assertIsNotNone(new_ant)
        """This should create a new object in the db and return it"""

        self.assertTrue(self.manager.name_exists(self.new_test_name2))
        """Now check if a new species was created"""

        existing_genus = Genus.objects.get_by_name(self.new_test_name2_genus)
        self.assertEqual(existing_genus.name, new_ant2.genus.name)
        """Check if genus was created too and if both genus names are equal"""

    def test_by_country(self):
        new_country = Country.objects.create(name='Test Country', code='test')
        ant1 = AntSpecies.objects.create(name='Myrmica testus')
        ant2 = AntSpecies.objects.create(name='Camponotus testus')
        ant3 = AntSpecies.objects.create(name='Formica testus')
        new_country.species_set.add(ant1, ant2, ant3)

        new_country = Country.objects.get(name='Test Country')
        ants = [ant.name for ant in new_country.species_set.all()]
        self.assertEqual(len(ants), 3)
        self.assertTrue(ant1.name in ants)
        self.assertTrue(ant2.name in ants)
        self.assertTrue(ant3.name in ants)

    def test_by_region(self):
        region_name = 'Test Region'
        region_code = 'test'
        country = Country.objects.get(code='de')
        new_region = Region.objects.create(
            name=region_name,
            code=region_code,
            country=country
        )

        ant1 = AntSpecies.objects.create(name='Myrmica testus')
        ant2 = AntSpecies.objects.create(name='Camponotus testus')
        ant3 = AntSpecies.objects.create(name='Formica testus')
        new_region.species_set.add(ant1, ant2, ant3)

        new_region = Region.objects.get(code=region_code)
        ants = [ant.name for ant in new_region.species_set.all()]
        self.assertEqual(len(ants), 3)
        self.assertTrue(ant1.name in ants)
        self.assertTrue(ant2.name in ants)
        self.assertTrue(ant3.name in ants)
