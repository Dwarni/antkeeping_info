from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from ants.models import (
    AntRegion,
    AntSize,
    AntSpecies,
    Distribution,
    Family,
    Genus,
    SpeciesDifficultyRating,
    SubFamily,
    Tribe,
)


class SpeciesFilterTest(TestCase):
    def setUp(self):
        self.family = Family.objects.create(name="Formicidae")
        self.subfamily = SubFamily.objects.create(name="Formicinae", family=self.family)
        self.tribe = Tribe.objects.create(name="Lasiini", sub_family=self.subfamily)
        self.genus = Genus.objects.create(name="Lasius", tribe=self.tribe)

        self.species = AntSpecies.objects.create(
            name="Lasius niger",
            valid=True,
            genus=self.genus,
            slug="lasius-niger",
            hibernation=AntSpecies.LONG_HIBERNATION,
            colony_structure=AntSpecies.MONOGYNOUS,
        )

        self.region = AntRegion.objects.create(name="Germany", code="DE")
        Distribution.objects.create(species=self.species, region=self.region)

        AntSize.objects.create(
            ant_species=self.species,
            type=AntSize.WORKER,
            minimum=3.5,
            maximum=5.0,
        )

        self.user = User.objects.create_user(
            username="testuser", password="password123"
        )
        SpeciesDifficultyRating.objects.create(
            species=self.species,
            user=self.user,
            difficulty=SpeciesDifficultyRating.BEGINNER,
        )

    def test_species_filter_view(self):
        response = self.client.get(reverse("species_filter"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Species Catalog & Filter")
        self.assertIn("subfamilies", response.context)
        self.assertIn("regions", response.context)
        self.assertIn("difficulty_choices", response.context)
        self.assertIn("genera", response.context)

    def test_species_filter_results_card_view(self):
        response = self.client.get(reverse("species_filter_results"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "species-card")
        self.assertContains(response, "Lasius niger")
        self.assertContains(response, "Beginner")
        self.assertContains(response, "3.5")

    def test_species_filter_results_list_view(self):
        response = self.client.get(reverse("species_filter_results") + "?view=list")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "species-list-table")
        self.assertContains(response, "Lasius niger")

    def test_filter_by_search(self):
        response = self.client.get(reverse("species_filter_results") + "?search=niger")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Lasius niger")

        response_empty = self.client.get(
            reverse("species_filter_results") + "?search=nonexistent"
        )
        self.assertEqual(response_empty.status_code, 200)
        self.assertContains(response_empty, "No matching ant species found")

    def test_filter_by_subfamily(self):
        response = self.client.get(
            reverse("species_filter_results") + f"?subfamily={self.subfamily.slug}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Lasius niger")

    def test_filter_by_region(self):
        response = self.client.get(reverse("species_filter_results") + "?region=DE")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Lasius niger")

    def test_filter_by_difficulty(self):
        response = self.client.get(reverse("species_filter_results") + "?difficulty=1")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Lasius niger")

        response_expert = self.client.get(
            reverse("species_filter_results") + "?difficulty=4"
        )
        self.assertEqual(response_expert.status_code, 200)
        self.assertContains(response_expert, "No matching ant species found")

    def test_species_model_properties(self):
        self.assertEqual(self.species.worker_size.minimum, 3.5)
        self.assertEqual(self.species.average_difficulty, 1.0)
        self.assertEqual(
            self.species.dominant_difficulty_level, SpeciesDifficultyRating.BEGINNER
        )
