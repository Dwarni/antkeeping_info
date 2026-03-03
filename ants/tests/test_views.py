from django.test import TestCase
from django.urls import reverse

from ants.models import AntRegion, AntSpecies, Distribution, Genus


class AntsViewsTest(TestCase):
    def setUp(self):
        self.genus = Genus.objects.create(name="Lasius")
        self.ant_species = AntSpecies.objects.create(
            name="Lasius niger", valid=True, genus=self.genus, slug="lasius-niger"
        )
        self.region = AntRegion.objects.create(name="Germany", code="DE")
        Distribution.objects.create(species=self.ant_species, region=self.region)

    def test_ant_species_detail(self):
        response = self.client.get(reverse("ant_detail", args=[self.ant_species.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Lasius niger")

    def test_top_lists_hub(self):
        response = self.client.get(reverse("antdb_top_lists"))
        self.assertEqual(response.status_code, 200)

    def test_top_lists_hub_with_ranking(self):
        response = self.client.get(
            reverse("antdb_top_lists") + "?ranking=countries-by-species&entries=10"
        )
        self.assertEqual(response.status_code, 200)

    def test_top_countries_ant_species_redirects(self):
        response = self.client.get(reverse("top_countries_ant_species"))
        self.assertEqual(response.status_code, 301)

    def test_top_countries_ant_genera_redirects(self):
        response = self.client.get(reverse("top_countries_ant_genera"))
        self.assertEqual(response.status_code, 301)

    def test_forbidden_in_eu_species_list(self):
        self.ant_species.forbidden_in_eu = True
        self.ant_species.save()

        response = self.client.get(reverse("forbidden_in_eu_species_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Lasius niger")
