from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from ants.models import (
    AntRegion,
    AntSpecies,
    Colony,
    ColonyJournalEntry,
    CommonName,
    Distribution,
    Family,
    FoodItem,
    Genus,
    SubFamily,
    Tribe,
)


class GlobalSearchViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="antkeeper", password="secretpassword")
        self.family = Family.objects.create(name="Formicidae")
        self.subfamily = SubFamily.objects.create(name="Formicinae", family=self.family)
        self.tribe = Tribe.objects.create(name="Lasiini", sub_family=self.subfamily)
        self.genus = Genus.objects.create(name="Lasius", tribe=self.tribe)

        self.species = AntSpecies.objects.create(
            name="Lasius niger",
            valid=True,
            genus=self.genus,
            slug="lasius-niger",
        )
        self.common_name = CommonName.objects.create(
            species=self.species,
            name="Schwarze Wegameise",
            language="de",
        )

        self.region = AntRegion.objects.create(
            name="Germany", code="DE", type="Country"
        )
        Distribution.objects.create(species=self.species, region=self.region)

        # Public colony and journal
        self.public_colony = Colony.objects.create(
            user=self.user,
            species=self.species,
            name="My Garden Colony",
            is_public=True,
        )
        self.public_journal = ColonyJournalEntry.objects.create(
            colony=self.public_colony,
            date="2026-05-10",
            note="Fed the colony sugar water and observed brood development.",
        )

        # Private colony and journal (should NOT appear in search)
        self.private_colony = Colony.objects.create(
            user=self.user,
            species=self.species,
            name="Secret Lab Colony",
            is_public=False,
        )
        self.private_journal = ColonyJournalEntry.objects.create(
            colony=self.private_colony,
            date="2026-05-12",
            note="Classified experiment notes about sugar water.",
        )

        # Food item
        self.food_item = FoodItem.objects.create(
            name="Honigwasser",
            category="SUGAR",
            description="Pure honey dissolved in warm water.",
        )

        self.url = reverse("search")

    def test_search_view_empty_query(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "search/search_results.html")
        self.assertContains(response, "What are you looking for?")
        self.assertEqual(response.context["total_results"], 0)

    def test_search_view_single_word_species(self):
        response = self.client.get(self.url, {"q": "niger"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["species_count"], 1)
        self.assertContains(response, "Lasius niger")

    def test_search_view_multi_token_species(self):
        response = self.client.get(self.url, {"q": "Lasius niger"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["species_count"], 1)
        self.assertContains(response, "Lasius niger")

    def test_search_view_by_common_name(self):
        response = self.client.get(self.url, {"q": "Wegameise"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["species_count"], 1)
        self.assertContains(response, "Lasius niger")

    def test_search_view_by_genus(self):
        response = self.client.get(self.url, {"q": "Lasius"})
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(response.context["species_count"], 1)
        self.assertContains(response, "Lasius niger")

    def test_search_view_finds_journals_and_excludes_private(self):
        response = self.client.get(self.url, {"q": "sugar water"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["journal_count"], 1)
        self.assertContains(response, "My Garden Colony")
        self.assertNotContains(response, "Secret Lab Colony")

    def test_search_view_finds_food_items(self):
        response = self.client.get(self.url, {"q": "Honigwasser"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["food_count"], 1)
        self.assertContains(response, "Honigwasser")

    def test_search_view_finds_regions(self):
        response = self.client.get(self.url, {"q": "Germany"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["region_count"], 1)
        self.assertContains(response, "Germany")

    def test_search_category_filter_tabs(self):
        response = self.client.get(self.url, {"q": "Lasius", "category": "species"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["selected_category"], "species")

    def test_search_typo_did_you_mean_genus(self):
        response = self.client.get(self.url, {"q": "Lasiuz"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_results"], 0)
        self.assertEqual(response.context["did_you_mean"], "Lasius")
        self.assertContains(response, "Did you mean:")
        self.assertContains(response, "Lasius")

    def test_search_typo_did_you_mean_species(self):
        response = self.client.get(self.url, {"q": "Lasius nyger"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_results"], 0)
        self.assertEqual(response.context["did_you_mean"], "Lasius niger")
        self.assertContains(response, "Did you mean:")
        self.assertContains(response, "Lasius niger")

    def test_search_autocomplete_api_endpoint(self):
        url = reverse("search_autocomplete")
        response = self.client.get(url, {"q": "Lasius"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("species", data)
        self.assertIn("food", data)
        self.assertIn("journals", data)
        self.assertIn("regions", data)
        self.assertGreaterEqual(data["total"], 1)
        species_titles = [s["title"] for s in data["species"]]
        self.assertIn("Lasius niger", species_titles)

    def test_search_autocomplete_short_query(self):
        url = reverse("search_autocomplete")
        response = self.client.get(url, {"q": "L"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total"], 0)
        self.assertEqual(data["results"], [])
