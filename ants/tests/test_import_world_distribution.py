from django.test import TestCase

from ants.models import AntRegion, AntSpecies, Distribution
from ants.services.antwiki import import_world_distribution

# Columns (tab-separated):
# 0: (unused), 1: genus, 2: species, 3: sub_species, 4: country,
# 5: sub_region, 6: occurrence ('Yes' = introduced, else native)
#
# Each row creates a country distribution and optionally a sub-region
# distribution. Four rows produce all six tested regions:
# Mexico, Chihuahua, Sonora, United States, Arizona, New Mexico
_WORLD_DISTRIBUTION_ROWS = [
    "\tAcanthostichus\tarizonensis\t\tMexico\tChihuahua\t",
    "\tAcanthostichus\tarizonensis\t\tMexico\tSonora\t",
    "\tAcanthostichus\tarizonensis\t\tUnited States\tArizona\t",
    "\tAcanthostichus\tarizonensis\t\tUnited States\tNew Mexico\t",
    # sub_species set → must be skipped
    "\tAcanthostichus\tarizonensis\tsubsp\tUnited States\tTexas\t",
]


class AntSpeciesManagerTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        va = AntSpecies.objects.create(name="Veromessor andrei")
        us = AntRegion.objects.create(name="United States", type="Country")
        ca = AntRegion.objects.create(name="California", type="Subregion", parent=us)
        Distribution.objects.create(species=va, region=us)
        Distribution.objects.create(species=va, region=ca)
        import_world_distribution(_WORLD_DISTRIBUTION_ROWS, True)

    def test_species_has_distribution(self):
        regions_to_test = [
            "Mexico",
            "Chihuahua",
            "Sonora",
            "United States",
            "Arizona",
            "New Mexico",
        ]
        ant = AntSpecies.objects.get(name="Acanthostichus arizonensis")
        for region_name in regions_to_test:
            d = ant.distribution.get(region__name=region_name)
            self.assertTrue(d.native)
