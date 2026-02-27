from django.test import TestCase

from ants.models import AntSpecies, Genus, SubFamily, Tribe
from ants.services.antwiki import import_valid_ant_species

# Columns (tab-separated):
# 0: taxon_name, 1: sub_family, 2: tribe, 3: genus, 4: species_group,
# 5: (unused), 6: sub_species, 7: (unused), 8: author, 9: year
_VALID_SPECIES_ROWS = [
    "Acromyrmex diasi\tMyrmicinae\tAttini\tAcromyrmex\t\t\t\t\tGonçalves\t1983",
    # sub_species name has 2 spaces → must not be imported
    "Acromyrmex coronatus rectispinus\tMyrmicinae\tAttini\tAcromyrmex\t\t\t\t\tSmith\t1858",  # noqa: E501
]


class AntSpeciesManagerTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        import_valid_ant_species(_VALID_SPECIES_ROWS)

    def test_species_import(self):
        name = "Acromyrmex diasi"
        genus = "Acromyrmex"
        author = "Gonçalves"
        year = 1983
        ad = AntSpecies.objects.filter(name=name)
        self.assertTrue(ad.exists())
        ad = ad.get()
        self.assertEqual(ad.genus.name, genus)
        self.assertEqual(ad.group, None)
        self.assertEqual(ad.author, author)
        self.assertEqual(ad.year, year)

    def test_genus_import(self):
        name = "Acromyrmex"
        tribe = "Attini"
        acro = Genus.objects.filter(name=name)
        self.assertTrue(acro.exists())
        acro = acro.get()
        self.assertEqual(acro.tribe.name, tribe)

    def test_tribe_import(self):
        name = "Attini"
        sub_family = "Myrmicinae"
        atti = Tribe.objects.filter(name=name)
        self.assertTrue(atti.exists())
        atti = atti.get()
        self.assertEqual(atti.sub_family.name, sub_family)

    def test_sub_family_import(self):
        name = "Myrmicinae"
        self.assertTrue(SubFamily.objects.filter(name=name).exists())

    def test_sub_species_not_imported(self):
        acr = AntSpecies.objects.filter(name="Acromyrmex coronatus rectispinus")
        self.assertFalse(acr.exists())
