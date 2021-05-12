from django.test import TestCase
from ants.models import AntSpecies, Genus, Tribe, SubFamily
from ants.services.antwiki import import_valid_ant_species

# from ants.models import AntSpecies


class AntSpeciesManagerTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        csv_file = open('ants/tests/valid_ant_species.txt', encoding="utf16") \
            .readlines(100000)[1:]
        import_valid_ant_species(csv_file)

    def test_species_import(self):
        name = 'Acromyrmex diasi'
        genus = 'Acromyrmex'
        author = 'Gonçalves'
        year = 1983
        ad = AntSpecies.objects.filter(name=name)
        self.assertTrue(ad.exists())
        ad = ad.get()
        self.assertEqual(ad.genus.name, genus)
        self.assertEqual(ad.group, None)
        self.assertEqual(ad.author, author)
        self.assertEqual(ad.year, year)

    def test_genus_import(self):
        name = 'Acromyrmex'
        tribe = 'Attini'
        acro = Genus.objects.filter(name=name)
        self.assertTrue(acro.exists())
        acro = acro.get()
        self.assertEqual(acro.tribe.name, tribe)

    def test_tribe_import(self):
        name = 'Attini'
        sub_family = 'Myrmicinae'
        atti = Tribe.objects.filter(name=name)
        self.assertTrue(atti.exists())
        atti = atti.get()
        self.assertEqual(atti.sub_family.name, sub_family)

    def test_sub_family_import(self):
        name = 'Myrmicinae'
        self.assertTrue(SubFamily.objects.filter(name=name).exists())

    def test_sub_species_not_imported(self):
        acr = AntSpecies.objects \
            .filter(name='Acromyrmex coronatus rectispinus')
        self.assertFalse(acr.exists())
