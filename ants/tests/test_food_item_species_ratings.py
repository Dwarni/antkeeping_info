from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from ants.models import AntSpecies, FoodItem, Genus, SpeciesFoodRating


def _make_species(name="Lasius niger", slug="lasius-niger"):
    genus = Genus.objects.create(name=name.split()[0])
    return AntSpecies.objects.create(name=name, valid=True, genus=genus, slug=slug)


def _make_food(name="Mealworms", category=FoodItem.PROTEIN):
    return FoodItem.objects.create(name=name, category=category)


def _make_vote(species, food_item, user, vote=SpeciesFoodRating.UP):
    return SpeciesFoodRating.objects.create(species=species, food_item=food_item, user=user, vote=vote)


class FoodItemSpeciesRatingsViewTest(TestCase):
    def setUp(self):
        self.species = _make_species()
        self.food_item = _make_food()
        self.url = reverse(
            "food_item_species_ratings",
            args=[self.food_item.pk, self.species.slug],
        )

    def test_no_votes_yet(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No votes yet")

    def test_lists_voter_and_direction(self):
        voter = User.objects.create_user(username="ant_fan", password="pass")
        _make_vote(self.species, self.food_item, voter, vote=SpeciesFoodRating.UP)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ant_fan")
        self.assertContains(response, "Accepts it")

    def test_downvote_shown(self):
        voter = User.objects.create_user(username="ant_fan", password="pass")
        _make_vote(self.species, self.food_item, voter, vote=SpeciesFoodRating.DOWN)
        response = self.client.get(self.url)
        self.assertContains(response, "Doesn&#x27;t accept it")

    def test_unknown_food_item_404(self):
        url = reverse("food_item_species_ratings", args=[999999, self.species.slug])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_unknown_species_404(self):
        url = reverse("food_item_species_ratings", args=[self.food_item.pk, "no-such-species"])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_only_votes_for_this_pair_are_shown(self):
        other_species = _make_species(name="Formica rufa", slug="formica-rufa")
        voter = User.objects.create_user(username="other_rater", password="pass")
        _make_vote(other_species, self.food_item, voter)
        response = self.client.get(self.url)
        self.assertContains(response, "No votes yet")
        self.assertNotContains(response, "other_rater")

    def test_no_edit_button_for_owner(self):
        owner = User.objects.create_user(username="owner", password="pass")
        _make_vote(self.species, self.food_item, owner)
        self.client.login(username="owner", password="pass")
        response = self.client.get(self.url)
        self.assertNotContains(response, "Edit")


class FoodOverviewLinksToRatingsViewTest(TestCase):
    def test_overview_links_to_species_ratings(self):
        species = _make_species()
        food_item = _make_food()
        rater = User.objects.create_user(username="linker", password="pass")
        _make_vote(species, food_item, rater)

        response = self.client.get(
            reverse("food_overview"), {"category": food_item.category}
        )
        ratings_url = reverse(
            "food_item_species_ratings", args=[food_item.pk, species.slug]
        )
        self.assertContains(response, ratings_url)


class FoodItemSpeciesRatingsListViewTest(TestCase):
    def test_returns_200_and_correct_content(self):
        species = _make_species()
        food_item = _make_food()
        rater = User.objects.create_user(username="ant_fan", password="pass")
        _make_vote(species, food_item, rater, vote=SpeciesFoodRating.UP)
        url = reverse("food_item_species_ratings_list", args=[food_item.pk, species.slug])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ant_fan")

    def test_unknown_food_item_404(self):
        species = _make_species()
        url = reverse("food_item_species_ratings_list", args=[999999, species.slug])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
