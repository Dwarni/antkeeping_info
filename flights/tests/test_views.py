from django.test import TestCase
from django.urls import reverse

from ants.models import AntSpecies, Genus, AntRegion
from flights.models import Flight

class FlightsViewsTest(TestCase):
    def setUp(self):
        self.genus = Genus.objects.create(name="Lasius")
        self.ant_species = AntSpecies.objects.create(
            name="Lasius niger", valid=True, genus=self.genus,
            slug="lasius-niger"
        )
        self.region = AntRegion.objects.create(name="Germany", code="DE", type="Country")
        self.flight = Flight.objects.create(
            ant_species=self.ant_species,
            date="2024-05-15",
            latitude=50.0,
            longitude=10.0,
            country=self.region,
            reviewed=True
        )

    def test_flights_map(self):
        response = self.client.get(reverse('flights_map'))
        self.assertEqual(response.status_code, 200)

    def test_flights_list(self):
        response = self.client.get(reverse('flights_list'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]['ant'], "Lasius niger")
