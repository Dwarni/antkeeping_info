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
        self.assertIsNotNone(AntRegion.objects
                             .find_by_name(self._name).first())

    def test_find_by_official_name(self):
        self.assertIsNotNone(AntRegion.objects.get_by_name(
            self._official_name))
        self.assertIsNotNone(AntRegion.objects.find_by_name(
            self._official_name).first())

    def test_find_by_antwiki_name(self):
        self.assertIsNotNone(AntRegion.objects.get_by_name(
            self._antwiki_name))
        self.assertIsNotNone(AntRegion.objects.find_by_name(
            self._antwiki_name).first())

    def test_no_object_found(self):
        name1 = 'blub blub bla'
        name2 = 'awiki blub'
        self.assertRaises(AntRegion.DoesNotExist,
                          AntRegion.objects.get_by_name, name1)
        self.assertIsNone(AntRegion.objects.find_by_name(name1).first())
        self.assertRaises(AntRegion.DoesNotExist,
                          AntRegion.objects.get_by_name, name2)
        self.assertIsNone(AntRegion.objects.find_by_name(name2).first())
