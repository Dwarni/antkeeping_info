from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from ants.models import FoodItem, Genus, AntSpecies, SpeciesDifficultyRating
from ants.tests.test_species_food_rating import _make_rating


def _make_species(name="Lasius niger", slug="lasius-niger"):
    genus = Genus.objects.create(name=name.split()[0])
    return AntSpecies.objects.create(name=name, valid=True, genus=genus, slug=slug)


def _make_food(name="Mealworms", category=FoodItem.PROTEIN):
    return FoodItem.objects.create(name=name, category=category)


class UserProfileViewRatingsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="owner", password="pass")
        self.other_user = User.objects.create_user(username="other", password="pass")
        self.url = reverse("user_profile")
        self.client.login(username="owner", password="pass")

    def test_requires_login(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_difficulty_ratings_scoped_to_user(self):
        species = _make_species()
        SpeciesDifficultyRating.objects.create(
            species=species, user=self.user, difficulty=SpeciesDifficultyRating.BEGINNER
        )
        SpeciesDifficultyRating.objects.create(
            species=species, user=self.other_user, difficulty=SpeciesDifficultyRating.EXPERT
        )
        response = self.client.get(self.url)
        ratings = list(response.context["difficulty_ratings"])
        self.assertEqual(len(ratings), 1)
        self.assertEqual(ratings[0].user, self.user)

    def test_food_rating_submissions_scoped_to_user(self):
        species = _make_species()
        food = _make_food()
        _make_rating(species, food, self.user, acceptance=4)
        _make_rating(species, food, self.other_user, acceptance=2)
        response = self.client.get(self.url)
        submissions = list(response.context["food_rating_submissions"])
        self.assertEqual(len(submissions), 1)
        self.assertEqual(submissions[0].user, self.user)


class UserProfileFoodRatingsViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="owner", password="pass")
        self.url = reverse("user_profile_food_ratings")

    def test_requires_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_returns_200_when_logged_in(self):
        self.client.login(username="owner", password="pass")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
