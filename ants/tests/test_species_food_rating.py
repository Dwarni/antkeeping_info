import io
import shutil
import tempfile

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.test import TestCase, override_settings
from django.urls import NoReverseMatch, reverse
from PIL import Image as PILImage

from ants.models import AntSpecies, FoodItem, FoodRatingSubmission, Genus, RatingPhoto, SpeciesFoodRating


def _make_species(name="Lasius niger", slug="lasius-niger"):
    genus = Genus.objects.create(name=name.split()[0])
    return AntSpecies.objects.create(name=name, valid=True, genus=genus, slug=slug)


def _make_food(name="Mealworms", category=FoodItem.PROTEIN):
    return FoodItem.objects.create(name=name, category=category)


def _make_rating(species, food_item, user, acceptance=3, condition=None, comment=""):
    """Create a FoodRatingSubmission + its SpeciesFoodRating link for one species."""
    submission = FoodRatingSubmission.objects.create(
        food_item=food_item, user=user, acceptance=acceptance, condition=condition, comment=comment,
    )
    return SpeciesFoodRating.objects.create(
        species=species, food_item=food_item, user=user, submission=submission,
    )


def _make_upload(width=3000, height=1500, name="photo.jpg"):
    buffer = io.BytesIO()
    PILImage.new("RGB", (width, height), color="blue").save(buffer, format="JPEG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/jpeg")


class FoodRatingSubmissionModelTest(TestCase):
    def setUp(self):
        self.species = _make_species()
        self.food = _make_food()
        self.user = User.objects.create_user(username="tester", password="pass")

    def test_create_rating(self):
        rating = _make_rating(self.species, self.food, self.user, acceptance=FoodRatingSubmission.THREE_STARS)
        self.assertEqual(rating.submission.acceptance, FoodRatingSubmission.THREE_STARS)
        self.assertEqual(rating.submission.comment, "")

    def test_create_rating_with_comment(self):
        rating = _make_rating(
            self.species, self.food, self.user,
            acceptance=FoodRatingSubmission.TWO_STARS, comment="Ate it slowly.",
        )
        self.assertEqual(rating.submission.comment, "Ate it slowly.")

    def test_unique_constraint_per_user_species_food_item(self):
        _make_rating(self.species, self.food, self.user, acceptance=FoodRatingSubmission.THREE_STARS)
        other_submission = FoodRatingSubmission.objects.create(
            food_item=self.food, user=self.user, acceptance=FoodRatingSubmission.ONE_STAR,
        )
        with self.assertRaises(IntegrityError):
            SpeciesFoodRating.objects.create(
                species=self.species, food_item=self.food, user=self.user, submission=other_submission,
            )

    def test_different_users_can_rate_same_species_and_food(self):
        other = User.objects.create_user(username="other", password="pass")
        _make_rating(self.species, self.food, self.user, acceptance=FoodRatingSubmission.THREE_STARS)
        _make_rating(self.species, self.food, other, acceptance=FoodRatingSubmission.ONE_STAR)
        self.assertEqual(self.species.food_ratings.count(), 2)

    def test_same_user_can_rate_different_food_items(self):
        honey = _make_food(name="Flower honey", category=FoodItem.SUGAR)
        _make_rating(self.species, self.food, self.user, acceptance=FoodRatingSubmission.THREE_STARS)
        _make_rating(self.species, honey, self.user, acceptance=FoodRatingSubmission.THREE_STARS)
        self.assertEqual(SpeciesFoodRating.objects.filter(user=self.user).count(), 2)

    def test_same_user_can_rate_same_food_on_different_species(self):
        other_species = _make_species(name="Formica rufa", slug="formica-rufa")
        _make_rating(self.species, self.food, self.user, acceptance=FoodRatingSubmission.THREE_STARS)
        _make_rating(other_species, self.food, self.user, acceptance=FoodRatingSubmission.ONE_STAR)
        self.assertEqual(SpeciesFoodRating.objects.filter(user=self.user).count(), 2)

    def test_create_rating_with_condition(self):
        rating = _make_rating(
            self.species, self.food, self.user,
            acceptance=FoodRatingSubmission.THREE_STARS, condition=FoodRatingSubmission.ALIVE,
        )
        self.assertEqual(rating.submission.condition, FoodRatingSubmission.ALIVE)

    def test_condition_optional_at_model_level(self):
        rating = _make_rating(self.species, self.food, self.user, acceptance=FoodRatingSubmission.THREE_STARS)
        self.assertIsNone(rating.submission.condition)

    def test_conditions_for_category_protein(self):
        self.assertEqual(
            FoodRatingSubmission.conditions_for_category(FoodItem.PROTEIN),
            [
                FoodRatingSubmission.ALIVE,
                FoodRatingSubmission.FRESHLY_KILLED,
                FoodRatingSubmission.SCALDED,
                FoodRatingSubmission.FROZEN,
                FoodRatingSubmission.DRIED,
            ],
        )

    def test_conditions_for_category_plant(self):
        self.assertEqual(
            FoodRatingSubmission.conditions_for_category(FoodItem.PLANT),
            [FoodRatingSubmission.FRESH, FoodRatingSubmission.FROZEN, FoodRatingSubmission.DRIED],
        )

    def test_conditions_for_category_not_applicable(self):
        for category in (FoodItem.SEEDS, FoodItem.SUGAR, FoodItem.OTHER):
            self.assertEqual(FoodRatingSubmission.conditions_for_category(category), [])

    def test_multiple_submissions_allowed_per_food_item_and_user(self):
        # No uniqueness constraint on FoodRatingSubmission itself -- a user can
        # have several submissions for the same food item over time (e.g. one
        # still owning species that weren't part of a later re-rating batch).
        FoodRatingSubmission.objects.create(
            food_item=self.food, user=self.user, acceptance=FoodRatingSubmission.THREE_STARS,
        )
        FoodRatingSubmission.objects.create(
            food_item=self.food, user=self.user, acceptance=FoodRatingSubmission.FOUR_STARS,
        )
        self.assertEqual(FoodRatingSubmission.objects.filter(food_item=self.food, user=self.user).count(), 2)


class AntSpeciesDetailFoodContextTest(TestCase):
    def setUp(self):
        self.species = _make_species()
        self.url = reverse("ant_detail", args=[self.species.slug])
        self.user1 = User.objects.create_user(username="user1", password="pass")
        self.user2 = User.objects.create_user(username="user2", password="pass")

    def test_context_no_food_items(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["food_by_category"], [])

    def test_context_food_item_no_ratings(self):
        _make_food()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        cats = response.context["food_by_category"]
        self.assertEqual(len(cats), 1)
        item_data = cats[0]["items"][0]
        self.assertEqual(item_data["total"], 0)
        self.assertIsNone(item_data["avg"])
        self.assertIsNone(item_data["user_rating"])

    def test_context_with_ratings(self):
        food = _make_food()
        _make_rating(self.species, food, self.user1, acceptance=FoodRatingSubmission.THREE_STARS)
        _make_rating(self.species, food, self.user2, acceptance=FoodRatingSubmission.THREE_STARS)
        response = self.client.get(self.url)
        item_data = response.context["food_by_category"][0]["items"][0]
        self.assertEqual(item_data["total"], 2)
        self.assertEqual(item_data["avg"], 3.0)

    def test_context_avg_mixed_ratings(self):
        food = _make_food()
        _make_rating(self.species, food, self.user1, acceptance=FoodRatingSubmission.ONE_STAR)
        _make_rating(self.species, food, self.user2, acceptance=FoodRatingSubmission.FIVE_STARS)
        response = self.client.get(self.url)
        item_data = response.context["food_by_category"][0]["items"][0]
        self.assertEqual(item_data["total"], 2)
        self.assertEqual(item_data["avg"], 3.0)

    def test_context_user_rating_anonymous(self):
        food = _make_food()
        _make_rating(self.species, food, self.user1, acceptance=FoodRatingSubmission.THREE_STARS)
        response = self.client.get(self.url)
        item_data = response.context["food_by_category"][0]["items"][0]
        self.assertIsNone(item_data["user_rating"])

    def test_context_user_rating_logged_in(self):
        food = _make_food()
        rating = _make_rating(self.species, food, self.user1, acceptance=FoodRatingSubmission.TWO_STARS)
        self.client.login(username="user1", password="pass")
        response = self.client.get(self.url)
        item_data = response.context["food_by_category"][0]["items"][0]
        self.assertEqual(item_data["user_rating"], rating)

    def test_context_user_rating_logged_in_no_own_rating(self):
        food = _make_food()
        _make_rating(self.species, food, self.user2, acceptance=FoodRatingSubmission.THREE_STARS)
        self.client.login(username="user1", password="pass")
        response = self.client.get(self.url)
        item_data = response.context["food_by_category"][0]["items"][0]
        self.assertIsNone(item_data["user_rating"])

    def test_category_grouping(self):
        _make_food(name="Mealworms", category=FoodItem.PROTEIN)
        _make_food(name="Flower honey", category=FoodItem.SUGAR)
        response = self.client.get(self.url)
        cats = response.context["food_by_category"]
        self.assertEqual(len(cats), 2)
        category_keys = [c["category_key"] for c in cats]
        self.assertIn(FoodItem.PROTEIN, category_keys)
        self.assertIn(FoodItem.SUGAR, category_keys)

    def test_category_order_follows_choices(self):
        _make_food(name="Sunflower seeds", category=FoodItem.SEEDS)
        _make_food(name="Mealworms", category=FoodItem.PROTEIN)
        response = self.client.get(self.url)
        cats = response.context["food_by_category"]
        self.assertEqual(cats[0]["category_key"], FoodItem.PROTEIN)
        self.assertEqual(cats[1]["category_key"], FoodItem.SEEDS)

    def test_rate_food_url_no_longer_exists(self):
        with self.assertRaises(NoReverseMatch):
            reverse("rate_food", args=[self.species.slug])

    def test_no_rating_form_rendered(self):
        _make_food()
        self.client.login(username="user1", password="pass")
        response = self.client.get(self.url)
        self.assertNotContains(response, 'name="acceptance"')
        self.assertContains(response, reverse("food_overview"))

    def test_own_rating_indicator_shown_when_logged_in(self):
        food = _make_food()
        _make_rating(self.species, food, self.user1, acceptance=FoodRatingSubmission.FOUR_STARS)
        self.client.login(username="user1", password="pass")
        response = self.client.get(self.url)
        self.assertContains(response, "You rated this")


class SubmitFoodRatingFromOverviewViewTest(TestCase):
    def setUp(self):
        self.species = _make_species()
        self.species2 = _make_species(name="Formica rufa", slug="formica-rufa")
        self.food = _make_food()
        self.url = reverse("food_overview_rate")
        self.user = User.objects.create_user(username="tester", password="pass")
        self.client.login(username="tester", password="pass")

    def test_protein_food_missing_condition_returns_400(self):
        response = self.client.post(
            self.url,
            {"species_id": [self.species.pk], "food_item_id": self.food.pk, "acceptance": 3},
        )
        self.assertEqual(response.status_code, 400)

    def test_protein_food_invalid_condition_returns_400(self):
        response = self.client.post(
            self.url,
            {
                "species_id": [self.species.pk],
                "food_item_id": self.food.pk,
                "acceptance": 3,
                "condition": FoodRatingSubmission.FRESH,
            },
        )
        self.assertEqual(response.status_code, 400)

    def test_protein_food_valid_condition_accepted(self):
        response = self.client.post(
            self.url,
            {
                "species_id": [self.species.pk],
                "food_item_id": self.food.pk,
                "acceptance": 3,
                "condition": FoodRatingSubmission.FROZEN,
            },
        )
        self.assertEqual(response.status_code, 200)
        rating = SpeciesFoodRating.objects.get(species=self.species, food_item=self.food, user=self.user)
        self.assertEqual(rating.submission.condition, FoodRatingSubmission.FROZEN)

    def test_plant_food_missing_condition_returns_400(self):
        leaf = _make_food(name="Bramble leaf", category=FoodItem.PLANT)
        response = self.client.post(
            self.url,
            {"species_id": [self.species.pk], "food_item_id": leaf.pk, "acceptance": 3},
        )
        self.assertEqual(response.status_code, 400)

    def test_plant_food_valid_condition_accepted(self):
        leaf = _make_food(name="Bramble leaf", category=FoodItem.PLANT)
        response = self.client.post(
            self.url,
            {
                "species_id": [self.species.pk],
                "food_item_id": leaf.pk,
                "acceptance": 3,
                "condition": FoodRatingSubmission.FRESH,
            },
        )
        self.assertEqual(response.status_code, 200)
        rating = SpeciesFoodRating.objects.get(species=self.species, food_item=leaf, user=self.user)
        self.assertEqual(rating.submission.condition, FoodRatingSubmission.FRESH)

    def test_seeds_food_condition_not_required(self):
        seeds = _make_food(name="Sunflower seeds", category=FoodItem.SEEDS)
        response = self.client.post(
            self.url,
            {"species_id": [self.species.pk], "food_item_id": seeds.pk, "acceptance": 3},
        )
        self.assertEqual(response.status_code, 200)
        rating = SpeciesFoodRating.objects.get(species=self.species, food_item=seeds, user=self.user)
        self.assertIsNone(rating.submission.condition)

    def test_single_species_creates_submission_and_link(self):
        response = self.client.post(
            self.url,
            {
                "species_id": [self.species.pk],
                "food_item_id": self.food.pk,
                "acceptance": 4,
                "condition": FoodRatingSubmission.ALIVE,
                "comment": "yum",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(FoodRatingSubmission.objects.count(), 1)
        rating = SpeciesFoodRating.objects.get(species=self.species, food_item=self.food, user=self.user)
        self.assertEqual(rating.submission.acceptance, 4)
        self.assertEqual(rating.submission.comment, "yum")

    def test_multi_species_batch_creates_one_submission_and_n_links(self):
        response = self.client.post(
            self.url,
            {
                "species_id": [self.species.pk, self.species2.pk],
                "food_item_id": self.food.pk,
                "acceptance": 4,
                "condition": FoodRatingSubmission.ALIVE,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(FoodRatingSubmission.objects.count(), 1)
        submission = FoodRatingSubmission.objects.get()
        links = SpeciesFoodRating.objects.filter(food_item=self.food, user=self.user)
        self.assertEqual(links.count(), 2)
        self.assertTrue(all(link.submission_id == submission.pk for link in links))

    def test_empty_species_list_returns_400(self):
        response = self.client.post(self.url, {"food_item_id": self.food.pk, "acceptance": 3})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(FoodRatingSubmission.objects.count(), 0)

    def test_one_invalid_species_id_rejects_whole_batch(self):
        response = self.client.post(
            self.url,
            {
                "species_id": [self.species.pk, 999999],
                "food_item_id": self.food.pk,
                "acceptance": 3,
                "condition": FoodRatingSubmission.ALIVE,
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(FoodRatingSubmission.objects.count(), 0)
        self.assertFalse(SpeciesFoodRating.objects.filter(species=self.species, food_item=self.food).exists())

    def test_duplicate_species_id_deduped(self):
        response = self.client.post(
            self.url,
            {
                "species_id": [self.species.pk, self.species.pk],
                "food_item_id": self.food.pk,
                "acceptance": 3,
                "condition": FoodRatingSubmission.ALIVE,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            SpeciesFoodRating.objects.filter(species=self.species, food_item=self.food, user=self.user).count(), 1,
        )

    def test_resubmit_species_alone_orphans_and_deletes_old_submission(self):
        self.client.post(
            self.url,
            {
                "species_id": [self.species.pk], "food_item_id": self.food.pk, "acceptance": 2,
                "condition": FoodRatingSubmission.ALIVE,
            },
        )
        old_submission_id = SpeciesFoodRating.objects.get(
            species=self.species, food_item=self.food, user=self.user
        ).submission_id

        self.client.post(
            self.url,
            {
                "species_id": [self.species.pk], "food_item_id": self.food.pk, "acceptance": 5,
                "condition": FoodRatingSubmission.ALIVE,
            },
        )

        self.assertFalse(FoodRatingSubmission.objects.filter(pk=old_submission_id).exists())
        rating = SpeciesFoodRating.objects.get(species=self.species, food_item=self.food, user=self.user)
        self.assertEqual(rating.submission.acceptance, 5)

    def test_resubmit_one_of_several_species_keeps_old_submission_for_the_rest(self):
        self.client.post(
            self.url,
            {
                "species_id": [self.species.pk, self.species2.pk],
                "food_item_id": self.food.pk,
                "acceptance": 2,
                "condition": FoodRatingSubmission.ALIVE,
            },
        )
        old_submission_id = SpeciesFoodRating.objects.get(
            species=self.species, food_item=self.food, user=self.user
        ).submission_id

        self.client.post(
            self.url,
            {
                "species_id": [self.species.pk], "food_item_id": self.food.pk, "acceptance": 5,
                "condition": FoodRatingSubmission.ALIVE,
            },
        )

        self.assertTrue(FoodRatingSubmission.objects.filter(pk=old_submission_id).exists())
        sibling = SpeciesFoodRating.objects.get(species=self.species2, food_item=self.food, user=self.user)
        self.assertEqual(sibling.submission_id, old_submission_id)
        self.assertEqual(sibling.submission.acceptance, 2)

        moved = SpeciesFoodRating.objects.get(species=self.species, food_item=self.food, user=self.user)
        self.assertNotEqual(moved.submission_id, old_submission_id)
        self.assertEqual(moved.submission.acceptance, 5)

    def test_resubmit_all_species_of_old_submission_deletes_it(self):
        self.client.post(
            self.url,
            {
                "species_id": [self.species.pk, self.species2.pk],
                "food_item_id": self.food.pk,
                "acceptance": 2,
                "condition": FoodRatingSubmission.ALIVE,
            },
        )
        old_submission_id = SpeciesFoodRating.objects.get(
            species=self.species, food_item=self.food, user=self.user
        ).submission_id

        self.client.post(
            self.url,
            {
                "species_id": [self.species.pk, self.species2.pk],
                "food_item_id": self.food.pk,
                "acceptance": 5,
                "condition": FoodRatingSubmission.ALIVE,
            },
        )

        self.assertFalse(FoodRatingSubmission.objects.filter(pk=old_submission_id).exists())
        self.assertEqual(FoodRatingSubmission.objects.count(), 1)

    def test_exceeds_max_species_returns_400(self):
        from ants.views import SubmitFoodRatingFromOverviewView

        extra_species = [
            _make_species(name=f"Genus{i} species", slug=f"species-{i}")
            for i in range(SubmitFoodRatingFromOverviewView.MAX_SPECIES_PER_SUBMISSION)
        ]
        response = self.client.post(
            self.url,
            {
                "species_id": [s.pk for s in extra_species] + [self.species.pk],
                "food_item_id": self.food.pk,
                "acceptance": 3,
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(FoodRatingSubmission.objects.count(), 0)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class SubmitFoodRatingFromOverviewImageUploadTest(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        from django.conf import settings
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.species = _make_species()
        self.food = _make_food()
        self.url = reverse("food_overview_rate")
        self.user = User.objects.create_user(username="tester", password="pass")
        self.client.login(username="tester", password="pass")

    def test_multiple_images_create_multiple_ordered_photos(self):
        response = self.client.post(
            self.url,
            {
                "species_id": [self.species.pk],
                "food_item_id": self.food.pk,
                "acceptance": 5,
                "condition": FoodRatingSubmission.ALIVE,
                "images": [_make_upload(name="a.jpg"), _make_upload(name="b.jpg")],
            },
        )
        self.assertEqual(response.status_code, 200)
        rating = SpeciesFoodRating.objects.get(species=self.species, food_item=self.food, user=self.user)
        photos = list(rating.submission.photos.all())
        self.assertEqual(len(photos), 2)
        self.assertEqual([p.ordering for p in photos], [0, 1])

    def test_image_gets_downscaled(self):
        response = self.client.post(
            self.url,
            {
                "species_id": [self.species.pk],
                "food_item_id": self.food.pk,
                "acceptance": 4,
                "condition": FoodRatingSubmission.ALIVE,
                "images": [_make_upload()],
            },
        )
        self.assertEqual(response.status_code, 200)
        rating = SpeciesFoodRating.objects.get(species=self.species, food_item=self.food, user=self.user)
        photo = rating.submission.photos.get()
        with PILImage.open(photo.image.path) as saved:
            self.assertEqual(max(saved.size), RatingPhoto.MAX_IMAGE_DIMENSION)

    def test_non_image_file_rejected_and_nothing_persisted(self):
        bogus = SimpleUploadedFile("notes.txt", b"not an image", content_type="text/plain")
        response = self.client.post(
            self.url,
            {
                "species_id": [self.species.pk],
                "food_item_id": self.food.pk,
                "acceptance": 4,
                "condition": FoodRatingSubmission.ALIVE,
                "images": [bogus],
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(SpeciesFoodRating.objects.filter(species=self.species, food_item=self.food).exists())
        self.assertEqual(FoodRatingSubmission.objects.count(), 0)

    def test_exceeds_max_photos_returns_400(self):
        from ants.views import SubmitFoodRatingFromOverviewView

        uploads = [
            _make_upload(name=f"{i}.jpg")
            for i in range(SubmitFoodRatingFromOverviewView.MAX_PHOTOS_PER_SUBMISSION + 1)
        ]
        response = self.client.post(
            self.url,
            {
                "species_id": [self.species.pk],
                "food_item_id": self.food.pk,
                "acceptance": 4,
                "condition": FoodRatingSubmission.ALIVE,
                "images": uploads,
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(FoodRatingSubmission.objects.count(), 0)


class FoodOverviewAggregationTest(TestCase):
    def setUp(self):
        self.species = _make_species()
        self.species2 = _make_species(name="Formica rufa", slug="formica-rufa")
        self.food = _make_food()
        self.user1 = User.objects.create_user(username="user1", password="pass")
        self.user2 = User.objects.create_user(username="user2", password="pass")

    def test_species_average_across_submissions(self):
        _make_rating(self.species, self.food, self.user1, acceptance=2)
        _make_rating(self.species, self.food, self.user2, acceptance=4)
        response = self.client.get(reverse("food_overview"), {"category": self.food.category})
        food_data = response.context["food_data"][0]
        top_species = {row["species_id"]: row for row in food_data["top_species"]}
        self.assertEqual(top_species[self.species.pk]["species_avg"], 3.0)
        self.assertEqual(food_data["overall_avg"], 3.0)
        self.assertEqual(food_data["total_ratings"], 2)

    def test_deleted_orphaned_submission_does_not_leak_into_average(self):
        self.client.login(username="user1", password="pass")
        url = reverse("food_overview_rate")
        self.client.post(url, {
            "species_id": [self.species.pk], "food_item_id": self.food.pk, "acceptance": 1,
            "condition": FoodRatingSubmission.ALIVE,
        })
        # Re-rate with a much higher score -- the old (1-star) submission is
        # orphaned and deleted, so it must not drag the average down.
        self.client.post(url, {
            "species_id": [self.species.pk], "food_item_id": self.food.pk, "acceptance": 5,
            "condition": FoodRatingSubmission.ALIVE,
        })

        response = self.client.get(reverse("food_overview"), {"category": self.food.category})
        food_data = response.context["food_data"][0]
        self.assertEqual(food_data["overall_avg"], 5.0)
        self.assertEqual(food_data["total_ratings"], 1)
