from django.test import TestCase
from ants.models import AntRegion


class AntSpeciesManagerTestCase(TestCase):
    _name = 'blub'
    _official_name = 'blub blub'
    _antwiki_name = 'awiki blub blub'

    @classmethod
    def setUpTestData(cls):
        AntRegion.objects.create(
            name=cls._name,
            official_name=cls._official_name,
            antwiki_name=cls._antwiki_name)

    def test_find_by_name(self):
        self.assertIsNotNone(AntRegion.objects.get_by_name(self._name))

    def test_find_by_official_name(self):
        self.assertIsNotNone(AntRegion.objects.get_by_name(
            self._official_name))

    def test_find_by_antwiki_name(self):
        self.assertIsNotNone(AntRegion.objects.get_by_name(
            self._antwiki_name))

    def test_no_object_found(self):
        self.assertRaises(AntRegion.DoesNotExist,
                          AntRegion.objects.get_by_name, 'blub blub bla')
        self.assertRaises(AntRegion.DoesNotExist,
                          AntRegion.objects.get_by_name, 'awiki blub')
