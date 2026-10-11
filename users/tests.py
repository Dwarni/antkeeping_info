import datetime

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from ants.models import (
    AntSpecies,
    Colony,
    ColonyJournalEntry,
    FoodItem,
    Genus,
    SpeciesDifficultyRating,
    SpeciesFoodRating,
)
from ants.tests.test_species_food_rating import _make_vote


def _make_species(name="Lasius niger", slug="lasius-niger"):
    genus, _ = Genus.objects.get_or_create(name=name.split()[0])
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
            species=species,
            user=self.other_user,
            difficulty=SpeciesDifficultyRating.EXPERT,
        )
        response = self.client.get(self.url)
        ratings = list(response.context["difficulty_ratings"])
        self.assertEqual(len(ratings), 1)
        self.assertEqual(ratings[0].user, self.user)
        self.assertEqual(response.context["difficulty_ratings_count"], 1)

    def test_food_ratings_scoped_to_user(self):
        species = _make_species()
        food = _make_food()
        _make_vote(species, food, self.user, vote=SpeciesFoodRating.UP)
        _make_vote(species, food, self.other_user, vote=SpeciesFoodRating.DOWN)
        response = self.client.get(self.url)
        ratings = list(response.context["food_ratings"])
        self.assertEqual(len(ratings), 1)
        self.assertEqual(ratings[0].user, self.user)
        self.assertEqual(response.context["food_ratings_count"], 1)

    def test_colonies_scoped_to_user(self):
        species = _make_species()
        Colony.objects.create(user=self.user, species=species, name="Mine")
        Colony.objects.create(user=self.other_user, species=species, name="Not mine")
        response = self.client.get(self.url)
        colonies = list(response.context["colonies"])
        self.assertEqual(len(colonies), 1)
        self.assertEqual(colonies[0].user, self.user)
        self.assertEqual(response.context["colonies_count"], 1)
        self.assertContains(response, reverse("user_profile_colonies"))


class UserProfileColoniesViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="owner", password="pass")
        self.other_user = User.objects.create_user(username="other", password="pass")
        self.url = reverse("user_profile_colonies")

    def test_requires_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_shows_user_colonies_only(self):
        self.client.login(username="owner", password="pass")
        species = _make_species()
        Colony.objects.create(user=self.user, species=species, name="My Solenopsis")
        Colony.objects.create(
            user=self.other_user, species=species, name="Secret Colony"
        )

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "My Solenopsis")
        self.assertNotContains(response, "Secret Colony")


class UserProfileJournalsViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="owner", password="pass")
        self.other_user = User.objects.create_user(username="other", password="pass")
        self.species = _make_species()
        self.colony1 = Colony.objects.create(
            user=self.user, species=self.species, name="Colony 1"
        )
        self.colony2 = Colony.objects.create(
            user=self.user, species=self.species, name="Colony 2"
        )
        self.url = reverse("user_profile_journals")

    def test_requires_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_shows_user_journal_entries_and_filtering(self):
        self.client.login(username="owner", password="pass")
        ColonyJournalEntry.objects.create(
            colony=self.colony1,
            date=datetime.date(2026, 5, 1),
            event_type=ColonyJournalEntry.EVENT_GENERAL,
            note="Note for colony 1",
        )
        ColonyJournalEntry.objects.create(
            colony=self.colony2,
            date=datetime.date(2026, 5, 2),
            event_type=ColonyJournalEntry.EVENT_FEEDING,
            note="Note for colony 2",
        )

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Note for colony 1")
        self.assertContains(response, "Note for colony 2")
        self.assertContains(response, "journal_image_lightbox")
        self.assertContains(response, "id=\"journal-image-lightbox\"")

        # Filter by colony
        response_filtered = self.client.get(f"{self.url}?colony={self.colony1.pk}")
        self.assertContains(response_filtered, "Note for colony 1")
        self.assertNotContains(response_filtered, "Note for colony 2")

        # Filter by event type
        response_event = self.client.get(
            f"{self.url}?event_type={ColonyJournalEntry.EVENT_FEEDING}"
        )
        self.assertNotContains(response_event, "Note for colony 1")
        self.assertContains(response_event, "Note for colony 2")


class UserProfileFoodRatingsViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="owner", password="pass")
        self.other_user = User.objects.create_user(username="other", password="pass")
        self.species = _make_species()
        self.food = _make_food()
        self.url = reverse("user_profile_food_ratings")

    def test_requires_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_returns_200_when_logged_in(self):
        self.client.login(username="owner", password="pass")
        _make_vote(self.species, self.food, self.user, vote=SpeciesFoodRating.UP)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.food.name)

    def test_htmx_fragment_request(self):
        self.client.login(username="owner", password="pass")
        _make_vote(self.species, self.food, self.user, vote=SpeciesFoodRating.UP)
        response = self.client.get(self.url, HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "users/profile_food_ratings_list.html")
        self.assertContains(response, self.food.name)


class UserProfileDifficultyRatingsViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="owner", password="pass")
        self.other_user = User.objects.create_user(username="other", password="pass")
        self.species = _make_species()
        self.url = reverse("user_profile_difficulty_ratings")

    def test_requires_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_shows_user_difficulty_ratings(self):
        self.client.login(username="owner", password="pass")
        SpeciesDifficultyRating.objects.create(
            species=self.species,
            user=self.user,
            difficulty=SpeciesDifficultyRating.BEGINNER,
            comment="Very easy ant species",
        )
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.species.name)
        self.assertContains(response, "Very easy ant species")
