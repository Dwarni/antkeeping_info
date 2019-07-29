from django.test import TestCase

from ants.models import AntRegion
from ants.services import antmaps


class AntmapsServiceTestCase(TestCase):
    def setUp(self):
        AntRegion.objects.create(name='Germany')
        AntRegion.objects.create(name='France')

    def test_get_entities(self):
        self.assertIsNotNone(antmaps.get_entities())

    def test_update_antmaps_ids(self):
        antmaps.update_antmaps_ids()
        france = AntRegion.objects.get(name='France')
        germany = AntRegion.objects.get(name='Germany')
        self.assertIsNotNone(france.antmaps_id)
        self.assertIsNotNone(germany.antmaps_id)
