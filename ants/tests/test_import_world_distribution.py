from django.test import TestCase
from ants.models import AntSpecies, AntRegion, Distribution
from ants.services.antwiki import import_world_distribution


class AntSpeciesManagerTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        va = AntSpecies.objects.create(name='Veromessor andrei')
        us = AntRegion.objects.create(name='United States', type='Country')
        ca = AntRegion.objects.create(
            name='California', type='Subregion', parent=us)
        Distribution.objects.create(species=va, region=us)
        Distribution.objects.create(species=va, region=ca)
        csv_file = open('ants/tests/world_distribution.txt',
                        encoding="utf16") \
            .readlines()[1:]
        import_world_distribution(csv_file, True)

    def test_species_has_distribution(self):
        regions_to_test = ['Mexico', 'Chihuahua', 'Sonora', 'United States',
                           'Arizona', 'New Mexico']
        ant = AntSpecies.objects.get(name='Acanthostichus arizonensis')
        for region_name in regions_to_test:
            d = ant.distribution.get(region__name=region_name)
            self.assertTrue(d.native)
