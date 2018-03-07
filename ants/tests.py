from django.test import TestCase
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from ants.models import AntSpecies, Genus
from ants.services import *


# Create your tests here.
class ServicesTestCase(TestCase):
    default_genus_name = 'Testius'
    default_species_name = default_genus_name + ' ' + 'rubra'

    def setUp(self):
        new_genus = Genus.objects.create(name=self.default_genus_name)
        AntSpecies.objects.create(name=self.default_species_name,
                                  genus=new_genus)

    def test_genus_exists(self):
        self.assertTrue(genus_exists(self.default_genus_name))
        self.assertFalse(genus_exists('testius'))
        self.assertFalse(genus_exists('Antus'))

    def test_get_genus(self):
        not_existing_genus_name = 'Antus'
        genus = get_genus(self.default_genus_name)
        self.assertEqual(genus.name, self.default_genus_name)
        self.assertRaises(
            ObjectDoesNotExist,
            get_genus,
            name=not_existing_genus_name
        )

    def test_add_genus(self):
        new_genus_name = 'Testiustwo'
        new_genus = add_genus(new_genus_name)
        found_genus = get_genus(new_genus_name)
        self.assertEqual(new_genus.name, found_genus.name)
        self.assertEqual(new_genus.id, found_genus.id)
        self.assertRaises(
            ValidationError,
            add_genus,
            name=new_genus_name.lower()
        )

    def test_get_or_create_genus(self):
        new_genus_name = 'Testiusthree'
        new_genus = get_or_create_genus(new_genus_name)
        found_genus = get_genus(new_genus_name)
        self.assertEqual(new_genus.name, found_genus.name)
        self.assertEqual(new_genus.id, found_genus.id)

        existing_genus = get_or_create_genus(self.default_genus_name)
        found_existing_genus = get_genus(self.default_genus_name)
        self.assertEqual(existing_genus.name, found_existing_genus.name)
        self.assertEqual(existing_genus.id, found_existing_genus.id)

        invalid_genus_name = 'testiusfour'
        self.assertRaises(
            ValidationError,
            get_or_create_genus,
            name=invalid_genus_name
        )

    def test_ant_exists(self):
        self.assertTrue(ant_exists(self.default_species_name))
        self.assertFalse(ant_exists(self.default_species_name.lower()))
        self.assertFalse(ant_exists('Antus existus'))

    def test_get_ant(self):
        not_existing_ant_name = 'Antus notexistus'
        ant = get_ant(self.default_species_name)
        self.assertEqual(ant.name, self.default_species_name)
        self.assertRaises(ObjectDoesNotExist, get_ant, not_existing_ant_name)

    def test_add_ant(self):
        name = 'Antus newus'
        genus_name = 'Antus'

        new_ant = add_ant(name)
        found_ant = get_ant(name)
        found_genus = get_genus(genus_name)

        self.assertEqual(new_ant.name, found_ant.name)
        self.assertEqual(new_ant.name, name)
        self.assertRaises(
            ValidationError,
            add_ant,
            name=name
        )
        self.assertRaises(
            ValidationError,
            add_ant,
            name='Lasius'
        )
        self.assertRaises(
            ValidationError,
            add_ant,
            name='lasius niger'
        )
        self.assertRaises(
            ValidationError,
            add_ant,
            name='Lasius Niger'
        )
        self.assertRaises(
            ValidationError,
            add_ant,
            name='Lasius Niger nigerum'
        )

    def test_get_or_create_ant_species(self):
        name = 'Lasius niger'
        genus_name = 'Lasius'

        new_ant = get_or_create_ant_species(name)
        found_ant = AntSpecies.objects.get(name=name)
        found_genus = Genus.objects.get(name=genus_name)

        self.assertEqual(new_ant.name, found_ant.name)
        self.assertEqual(new_ant.name, name)
        self.assertRaises(
            ValidationError,
            get_or_create_ant_species,
            name='Lasius'
        )
        self.assertRaises(
            ValidationError,
            get_or_create_ant_species,
            name='lasius niger'
        )
        self.assertRaises(
            ValidationError,
            get_or_create_ant_species,
            name='Lasius Niger'
        )
        self.assertRaises(
            ValidationError,
            get_or_create_ant_species,
            name='Lasius Niger nigerum'
        )
