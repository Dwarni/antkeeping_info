from django.contrib.auth.models import User
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

    def test_flights_list_year_filter(self):
        response = self.client.get(reverse('flights_list') + '?year=2024')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)

    def test_flights_list_year_filter_no_match(self):
        response = self.client.get(reverse('flights_list') + '?year=2000')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 0)


class FlightsReviewViewsTest(TestCase):
    def setUp(self):
        self.genus = Genus.objects.create(name="Lasius")
        self.ant_species = AntSpecies.objects.create(
            name="Lasius niger", valid=True, genus=self.genus)
        self.region = AntRegion.objects.create(name="Germany", code="DE", type="Country")
        self.flight = Flight.objects.create(
            ant_species=self.ant_species,
            date="2024-05-15",
            latitude=50.0,
            longitude=10.0,
            country=self.region,
            reviewed=False
        )
        self.staff_user = User.objects.create_user(
            username="staff", password="pass", is_staff=True)

    def test_review_list_requires_staff(self):
        response = self.client.get(reverse('flights_review_list'))
        self.assertNotEqual(response.status_code, 200)

    def test_review_list_accessible_by_staff(self):
        self.client.login(username="staff", password="pass")
        response = self.client.get(reverse('flights_review_list'))
        self.assertEqual(response.status_code, 200)

    def test_review_list_shows_unreviewed_flights(self):
        self.client.login(username="staff", password="pass")
        response = self.client.get(reverse('flights_review_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Lasius niger")

    def test_review_list_hides_reviewed_flights(self):
        self.flight.reviewed = True
        self.flight.save()
        self.client.login(username="staff", password="pass")
        response = self.client.get(reverse('flights_review_list'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Lasius niger")
