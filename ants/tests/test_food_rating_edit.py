import shutil
import tempfile

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from ants.models import FoodItem, FoodRatingSubmission, RatingPhoto, SpeciesFoodRating
from ants.tests.test_species_food_rating import _make_food, _make_rating, _make_species, _make_upload


class FoodRatingSubmissionEditViewOwnershipTest(TestCase):
    def setUp(self):
        self.species = _make_species()
        self.food = _make_food()
        self.user = User.objects.create_user(username="owner", password="pass")
        self.other_user = User.objects.create_user(username="other", password="pass")
        self.rating = _make_rating(self.species, self.food, self.user, acceptance=3, condition=FoodRatingSubmission.ALIVE)
        self.url = reverse("food_rating_edit", args=[self.rating.submission_id])

    def _post_data(self, **overrides):
        data = {
            "species_id": [self.species.pk],
            "acceptance": 4,
            "condition": FoodRatingSubmission.FROZEN,
            "comment": "updated",
        }
        data.update(overrides)
        return data

    def test_get_requires_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_post_requires_login(self):
        response = self.client.post(self.url, self._post_data())
        self.assertEqual(response.status_code, 302)

    def test_get_as_owner_succeeds(self):
        self.client.login(username="owner", password="pass")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_get_as_other_user_forbidden(self):
        self.client.login(username="other", password="pass")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_post_as_other_user_forbidden(self):
        self.client.login(username="other", password="pass")
        response = self.client.post(self.url, self._post_data())
        self.assertEqual(response.status_code, 403)
        self.rating.submission.refresh_from_db()
        self.assertEqual(self.rating.submission.acceptance, 3)

    def test_nonexistent_submission_404(self):
        self.client.login(username="owner", password="pass")
        url = reverse("food_rating_edit", args=[999999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


class FoodRatingSubmissionEditViewUpdateTest(TestCase):
    def setUp(self):
        self.species = _make_species()
        self.species2 = _make_species(name="Formica rufa", slug="formica-rufa")
        self.food = _make_food()
        self.user = User.objects.create_user(username="owner", password="pass")
        self.rating = _make_rating(self.species, self.food, self.user, acceptance=3, condition=FoodRatingSubmission.ALIVE)
        self.submission_id = self.rating.submission_id
        self.url = reverse("food_rating_edit", args=[self.submission_id])
        self.client.login(username="owner", password="pass")

    def test_updates_submission_in_place(self):
        response = self.client.post(
            self.url,
            {
                "species_id": [self.species.pk],
                "acceptance": 5,
                "condition": FoodRatingSubmission.FROZEN,
                "comment": "much better now",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["HX-Trigger"], "foodRatingEditSuccess")
        self.assertEqual(FoodRatingSubmission.objects.count(), 1)
        submission = FoodRatingSubmission.objects.get(pk=self.submission_id)
        self.assertEqual(submission.acceptance, 5)
        self.assertEqual(submission.condition, FoodRatingSubmission.FROZEN)
        self.assertEqual(submission.comment, "much better now")

    def test_empty_species_list_returns_400_and_changes_nothing(self):
        response = self.client.post(
            self.url,
            {"acceptance": 5, "condition": FoodRatingSubmission.FROZEN},
        )
        self.assertEqual(response.status_code, 400)
        submission = FoodRatingSubmission.objects.get(pk=self.submission_id)
        self.assertEqual(submission.acceptance, 3)

    def test_removing_species_deletes_only_that_link(self):
        # Rating shares a submission across both species.
        SpeciesFoodRating.objects.filter(pk=self.rating.pk).update(submission_id=self.submission_id)
        link2 = SpeciesFoodRating.objects.create(
            species=self.species2, food_item=self.food, user=self.user,
            submission_id=self.submission_id,
        )
        response = self.client.post(
            self.url,
            {
                "species_id": [self.species2.pk],
                "acceptance": 5,
                "condition": FoodRatingSubmission.FROZEN,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            SpeciesFoodRating.objects.filter(species=self.species, food_item=self.food, user=self.user).exists()
        )
        link2.refresh_from_db()
        self.assertEqual(link2.submission_id, self.submission_id)

    def test_adding_species_that_had_a_different_submission_reassigns_and_orphans(self):
        other_rating = _make_rating(self.species2, self.food, self.user, acceptance=1)
        old_submission_id = other_rating.submission_id

        response = self.client.post(
            self.url,
            {
                "species_id": [self.species.pk, self.species2.pk],
                "acceptance": 5,
                "condition": FoodRatingSubmission.FROZEN,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(FoodRatingSubmission.objects.filter(pk=old_submission_id).exists())
        moved = SpeciesFoodRating.objects.get(species=self.species2, food_item=self.food, user=self.user)
        self.assertEqual(moved.submission_id, self.submission_id)

    def test_condition_required_for_protein_missing_returns_400(self):
        response = self.client.post(
            self.url,
            {"species_id": [self.species.pk], "acceptance": 5},
        )
        self.assertEqual(response.status_code, 400)

    def test_condition_invalid_for_category_returns_400(self):
        response = self.client.post(
            self.url,
            {"species_id": [self.species.pk], "acceptance": 5, "condition": FoodRatingSubmission.FRESH},
        )
        self.assertEqual(response.status_code, 400)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class FoodRatingSubmissionEditViewPhotoTest(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        from django.conf import settings
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.species = _make_species()
        self.food = _make_food()
        self.user = User.objects.create_user(username="owner", password="pass")
        self.rating = _make_rating(self.species, self.food, self.user, acceptance=3, condition=FoodRatingSubmission.ALIVE)
        self.submission = self.rating.submission
        self.photo1 = RatingPhoto.objects.create(submission=self.submission, image=_make_upload(name="a.jpg"), ordering=0)
        self.photo2 = RatingPhoto.objects.create(submission=self.submission, image=_make_upload(name="b.jpg"), ordering=1)
        self.url = reverse("food_rating_edit", args=[self.submission.pk])
        self.client.login(username="owner", password="pass")

    def test_kept_photos_survive_edit_without_touching_photos(self):
        response = self.client.post(
            self.url,
            {"species_id": [self.species.pk], "acceptance": 4, "condition": FoodRatingSubmission.FROZEN},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.submission.photos.count(), 2)

    def test_remove_photo_id_deletes_only_that_photo(self):
        response = self.client.post(
            self.url,
            {
                "species_id": [self.species.pk],
                "acceptance": 4,
                "condition": FoodRatingSubmission.FROZEN,
                "remove_photo_id": [self.photo1.pk],
            },
        )
        self.assertEqual(response.status_code, 200)
        remaining = list(self.submission.photos.all())
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0].pk, self.photo2.pk)

    def test_new_photo_appended_with_correct_ordering(self):
        response = self.client.post(
            self.url,
            {
                "species_id": [self.species.pk],
                "acceptance": 4,
                "condition": FoodRatingSubmission.FROZEN,
                "images": [_make_upload(name="c.jpg")],
            },
        )
        self.assertEqual(response.status_code, 200)
        photos = list(self.submission.photos.order_by("ordering"))
        self.assertEqual(len(photos), 3)
        self.assertEqual(photos[-1].ordering, 2)

    def test_foreign_photo_id_rejected(self):
        other_user = User.objects.create_user(username="other", password="pass")
        other_rating = _make_rating(self.species, self.food, other_user, acceptance=2)
        foreign_photo = RatingPhoto.objects.create(
            submission=other_rating.submission, image=_make_upload(name="z.jpg"), ordering=0
        )
        response = self.client.post(
            self.url,
            {
                "species_id": [self.species.pk],
                "acceptance": 4,
                "condition": FoodRatingSubmission.FROZEN,
                "remove_photo_id": [foreign_photo.pk],
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertTrue(RatingPhoto.objects.filter(pk=foreign_photo.pk).exists())

    def test_exceeding_photo_cap_returns_400(self):
        from ants.views import FoodRatingSubmissionEditView

        max_photos = FoodRatingSubmissionEditView.MAX_PHOTOS_PER_SUBMISSION
        uploads = [_make_upload(name=f"extra{i}.jpg") for i in range(max_photos)]
        response = self.client.post(
            self.url,
            {
                "species_id": [self.species.pk],
                "acceptance": 4,
                "condition": FoodRatingSubmission.FROZEN,
                "images": uploads,
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.submission.photos.count(), 2)
