import shutil
import tempfile

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from ants.models import AntSpecies, FoodItem, FoodRatingSubmission, Genus, RatingPhoto, SpeciesFoodRating


def _make_species(name="Lasius niger", slug="lasius-niger"):
    genus = Genus.objects.create(name=name.split()[0])
    return AntSpecies.objects.create(name=name, valid=True, genus=genus, slug=slug)


def _make_food(name="Mealworms", category=FoodItem.PROTEIN):
    return FoodItem.objects.create(name=name, category=category)


def _make_rating(species, food_item, user, acceptance=5, condition=None, comment=""):
    submission = FoodRatingSubmission.objects.create(
        food_item=food_item, user=user, acceptance=acceptance, condition=condition, comment=comment,
    )
    return SpeciesFoodRating.objects.create(
        species=species, food_item=food_item, user=user, submission=submission,
    )


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
        _make_rating(self.species, self.food_item, rater, acceptance=5, comment="Devoured immediately.")
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

    def test_condition_displayed_when_present(self):
        rater = User.objects.create_user(username="ant_fan", password="pass")
        _make_rating(self.species, self.food_item, rater, acceptance=5, condition=FoodRatingSubmission.ALIVE)
        response = self.client.get(self.url)
        self.assertContains(response, "Alive")

    def test_condition_not_shown_when_absent(self):
        rater = User.objects.create_user(username="ant_fan", password="pass")
        _make_rating(self.species, self.food_item, rater, acceptance=5)
        response = self.client.get(self.url)
        self.assertNotContains(response, "badge bg-light")

    def test_only_ratings_for_this_pair_are_shown(self):
        other_species = _make_species(name="Formica rufa", slug="formica-rufa")
        rater = User.objects.create_user(username="other_rater", password="pass")
        _make_rating(other_species, self.food_item, rater, acceptance=3, comment="Different species comment.")
        response = self.client.get(self.url)
        self.assertContains(response, "No ratings yet")
        self.assertNotContains(response, "Different species comment.")


class FoodOverviewLinksToRatingsViewTest(TestCase):
    def test_overview_links_to_species_ratings(self):
        species = _make_species()
        food_item = _make_food()
        rater = User.objects.create_user(username="linker", password="pass")
        _make_rating(species, food_item, rater, acceptance=4)

        response = self.client.get(
            reverse("food_overview"), {"category": food_item.category}
        )
        ratings_url = reverse(
            "food_item_species_ratings", args=[food_item.pk, species.slug]
        )
        self.assertContains(response, ratings_url)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class FoodItemSpeciesRatingsPhotoDisplayTest(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        from django.conf import settings
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)

    def test_photos_rendered_on_ratings_list_page(self):
        from ants.tests.test_species_food_rating import _make_upload

        species = _make_species()
        food = _make_food()
        user = User.objects.create_user(username="shutterbug", password="pass")
        rating = _make_rating(species, food, user, acceptance=5)
        RatingPhoto.objects.create(submission=rating.submission, image=_make_upload(), ordering=0)
        RatingPhoto.objects.create(submission=rating.submission, image=_make_upload(name="b.jpg"), ordering=1)

        url = reverse("food_item_species_ratings", args=[food.pk, species.slug])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Photo by shutterbug", count=2)

    def test_no_photos_renders_nothing_extra(self):
        species = _make_species()
        food = _make_food()
        user = User.objects.create_user(username="no_photos", password="pass")
        _make_rating(species, food, user, acceptance=5)

        url = reverse("food_item_species_ratings", args=[food.pk, species.slug])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Photo by no_photos")
