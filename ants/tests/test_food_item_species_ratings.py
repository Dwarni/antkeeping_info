from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from ants.models import AntSpecies, FoodItem, Genus, SpeciesFoodRating


def _make_species(name="Lasius niger", slug="lasius-niger"):
    genus = Genus.objects.create(name=name.split()[0])
    return AntSpecies.objects.create(name=name, valid=True, genus=genus, slug=slug)


def _make_food(name="Mealworms", category=FoodItem.PROTEIN):
    return FoodItem.objects.create(name=name, category=category)


class FoodItemSpeciesRatingsViewTest(TestCase):
    def setUp(self):
        self.species = _make_species()
        self.food_item = _make_food()
        self.url = reverse(
            "food_item_species_ratings",
            args=[self.food_item.pk, self.species.slug],
        )

    def test_no_ratings_yet(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No ratings yet")

    def test_lists_rater_and_comment(self):
        rater = User.objects.create_user(username="ant_fan", password="pass")
        SpeciesFoodRating.objects.create(
            species=self.species,
            food_item=self.food_item,
            user=rater,
            acceptance=5,
            comment="Devoured immediately.",
        )
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ant_fan")
        self.assertContains(response, "Devoured immediately.")

    def test_unknown_food_item_404(self):
        url = reverse("food_item_species_ratings", args=[999999, self.species.slug])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_unknown_species_404(self):
        url = reverse("food_item_species_ratings", args=[self.food_item.pk, "no-such-species"])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_only_ratings_for_this_pair_are_shown(self):
        other_species = _make_species(name="Formica rufa", slug="formica-rufa")
        rater = User.objects.create_user(username="other_rater", password="pass")
        SpeciesFoodRating.objects.create(
            species=other_species,
            food_item=self.food_item,
            user=rater,
            acceptance=3,
            comment="Different species comment.",
        )
        response = self.client.get(self.url)
        self.assertContains(response, "No ratings yet")
        self.assertNotContains(response, "Different species comment.")


class FoodOverviewLinksToRatingsViewTest(TestCase):
    def test_overview_links_to_species_ratings(self):
        species = _make_species()
        food_item = _make_food()
        rater = User.objects.create_user(username="linker", password="pass")
        SpeciesFoodRating.objects.create(
            species=species, food_item=food_item, user=rater, acceptance=4
        )

        response = self.client.get(
            reverse("food_overview"), {"category": food_item.category}
        )
        ratings_url = reverse(
            "food_item_species_ratings", args=[food_item.pk, species.slug]
        )
        self.assertContains(response, ratings_url)
