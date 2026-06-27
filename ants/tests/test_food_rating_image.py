import io
import shutil
import tempfile

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image as PILImage

from ants.models import AntSpecies, FoodItem, Genus, SpeciesFoodRating

_MEDIA_ROOT = tempfile.mkdtemp()


def _make_species(name="Lasius niger", slug="lasius-niger"):
    genus = Genus.objects.create(name=name.split()[0])
    return AntSpecies.objects.create(name=name, valid=True, genus=genus, slug=slug)


def _make_food(name="Mealworms", category=FoodItem.PROTEIN):
    return FoodItem.objects.create(name=name, category=category)


def _make_upload(width=3000, height=1500, name="photo.jpg"):
    buffer = io.BytesIO()
    PILImage.new("RGB", (width, height), color="blue").save(buffer, format="JPEG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/jpeg")


@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class RateFoodImageUploadTest(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.species = _make_species()
        self.food = _make_food()
        self.url = reverse("rate_food", args=[self.species.slug])
        self.user = User.objects.create_user(username="tester", password="pass")
        self.client.login(username="tester", password="pass")

    def test_uploading_image_attaches_and_downscales_it(self):
        response = self.client.post(
            self.url,
            {
                "food_item_id": self.food.pk,
                "acceptance": 4,
                "condition": SpeciesFoodRating.ALIVE,
                "image": _make_upload(),
            },
        )
        self.assertEqual(response.status_code, 200)
        rating = SpeciesFoodRating.objects.get(species=self.species, food_item=self.food, user=self.user)
        self.assertTrue(rating.image)
        with PILImage.open(rating.image.path) as saved:
            self.assertEqual(max(saved.size), SpeciesFoodRating.MAX_IMAGE_DIMENSION)

    def test_non_image_file_rejected(self):
        bogus = SimpleUploadedFile("notes.txt", b"not an image", content_type="text/plain")
        response = self.client.post(
            self.url,
            {
                "food_item_id": self.food.pk,
                "acceptance": 4,
                "condition": SpeciesFoodRating.ALIVE,
                "image": bogus,
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(SpeciesFoodRating.objects.filter(species=self.species, food_item=self.food).exists())

    def test_updating_rating_without_new_image_keeps_existing_one(self):
        self.client.post(
            self.url,
            {
                "food_item_id": self.food.pk,
                "acceptance": 4,
                "condition": SpeciesFoodRating.ALIVE,
                "image": _make_upload(),
            },
        )
        rating = SpeciesFoodRating.objects.get(species=self.species, food_item=self.food, user=self.user)
        original_image_name = rating.image.name

        self.client.post(
            self.url,
            {
                "food_item_id": self.food.pk,
                "acceptance": 2,
                "condition": SpeciesFoodRating.DRIED,
                "comment": "changed my mind",
            },
        )
        rating.refresh_from_db()
        self.assertEqual(rating.acceptance, SpeciesFoodRating.TWO_STARS)
        self.assertEqual(rating.image.name, original_image_name)


@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class FoodOverviewRateImageUploadTest(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.species = _make_species()
        self.food = _make_food()
        self.url = reverse("food_overview_rate")
        self.user = User.objects.create_user(username="tester", password="pass")
        self.client.login(username="tester", password="pass")

    def test_uploading_image_attaches_it(self):
        response = self.client.post(
            self.url,
            {
                "species_id": self.species.pk,
                "food_item_id": self.food.pk,
                "acceptance": 5,
                "condition": SpeciesFoodRating.ALIVE,
                "image": _make_upload(),
            },
        )
        self.assertEqual(response.status_code, 200)
        rating = SpeciesFoodRating.objects.get(species=self.species, food_item=self.food, user=self.user)
        self.assertTrue(rating.image)

    def test_non_image_file_rejected(self):
        bogus = SimpleUploadedFile("notes.txt", b"not an image", content_type="text/plain")
        response = self.client.post(
            self.url,
            {
                "species_id": self.species.pk,
                "food_item_id": self.food.pk,
                "acceptance": 5,
                "condition": SpeciesFoodRating.ALIVE,
                "image": bogus,
            },
        )
        self.assertEqual(response.status_code, 400)


@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class FoodItemSpeciesRatingsImageDisplayTest(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(_MEDIA_ROOT, ignore_errors=True)

    def test_photo_link_rendered_on_ratings_list_page(self):
        species = _make_species()
        food = _make_food()
        user = User.objects.create_user(username="shutterbug", password="pass")
        SpeciesFoodRating.objects.create(
            species=species, food_item=food, user=user, acceptance=5, image=_make_upload()
        )
        url = reverse("food_item_species_ratings", args=[food.pk, species.slug])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<img")
