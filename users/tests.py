import datetime
import io

from allauth.socialaccount.models import SocialAccount
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from PIL import Image

from ants.models import (
    AntSpecies,
    Colony,
    ColonyJournalEntry,
    FoodItem,
    SpeciesDifficultyRating,
    SpeciesFoodRating,
)
from users.models import UserProfile, validate_avatar_size
from users.templatetags.user_tags import user_avatar


def _make_species(name="Lasius niger"):
    return AntSpecies.objects.create(name=name, slug=name.lower().replace(" ", "-"))


def _make_food(name="Mealworm"):
    return FoodItem.objects.create(name=name, category=FoodItem.PROTEIN)


def _make_vote(species, food, user, vote=SpeciesFoodRating.UP):
    return SpeciesFoodRating.objects.create(
        species=species, food_item=food, user=user, vote=vote
    )


def _create_test_image(format="PNG", size=(64, 64)):
    file = io.BytesIO()
    image = Image.new("RGBA", size=size, color=(255, 0, 0))
    image.save(file, format=format)
    file.seek(0)
    return SimpleUploadedFile(
        f"test.{format.lower()}", file.read(), content_type=f"image/{format.lower()}"
    )


class UserProfileViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="secretpassword")
        self.url = reverse("user_profile")

    def test_requires_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_returns_200_when_logged_in(self):
        self.client.login(username="testuser", password="secretpassword")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "@testuser")
        self.assertContains(response, reverse("user_profile_settings"))

    def test_shows_counts(self):
        self.client.login(username="testuser", password="secretpassword")
        species = _make_species()
        Colony.objects.create(user=self.user, species=species, name="Colony 1")

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

    def test_status_filtering_in_profile_colonies(self):
        self.client.login(username="owner", password="pass")
        species = _make_species()
        Colony.objects.create(user=self.user, species=species, name="Active 1", status=Colony.ACTIVE)
        Colony.objects.create(user=self.user, species=species, name="Founding 1", status=Colony.FOUNDING)
        Colony.objects.create(user=self.user, species=species, name="Hibernating 1", status=Colony.HIBERNATING)
        Colony.objects.create(user=self.user, species=species, name="Dead 1", status=Colony.DEAD)

        resp = self.client.get(self.url)
        self.assertEqual(resp.context["total_colonies"], 4)
        self.assertEqual(resp.context["active_colonies"], 1)
        self.assertEqual(resp.context["founding_colonies"], 1)
        self.assertEqual(resp.context["hibernating_colonies"], 1)
        self.assertEqual(resp.context["archived_colonies"], 1)

        resp_act = self.client.get(f"{self.url}?status=active")
        self.assertEqual(len(resp_act.context["colonies"]), 1)
        self.assertEqual(resp_act.context["colonies"][0].name, "Active 1")

    def test_colony_volksstaerke_display_in_profile_colonies(self):
        from ants.models import ColonyCensus
        self.client.login(username="owner", password="pass")
        species = _make_species()
        c = Colony.objects.create(user=self.user, species=species, name="Growing Colony", status=Colony.ACTIVE)
        ColonyCensus.objects.create(colony=c, queens=1, workers=42)

        resp = self.client.get(self.url)
        self.assertContains(resp, "1 👑 • 42 🐜")


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


class UserProfileFoodRatingsViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="owner", password="pass")
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


class UserProfileDifficultyRatingsViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="owner", password="pass")
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


class UserProfileModelAndAvatarTest(TestCase):
    def test_user_profile_auto_created_on_user_creation(self):
        user = User.objects.create_user(username="antfan", password="secretpassword")
        self.assertTrue(hasattr(user, "profile"))
        self.assertIsInstance(user.profile, UserProfile)
        self.assertEqual(str(user.profile), "Profile of antfan")
        self.assertIsNone(user.profile.avatar_url)

    def test_validate_avatar_size(self):
        small_file = SimpleUploadedFile("small.jpg", b"123", content_type="image/jpeg")
        # Should not raise
        validate_avatar_size(small_file)

        large_bytes = b"x" * (6 * 1024 * 1024)
        large_file = SimpleUploadedFile("large.jpg", large_bytes, content_type="image/jpeg")
        with self.assertRaises(ValidationError):
            validate_avatar_size(large_file)

    def test_user_avatar_template_tag(self):
        user = User.objects.create_user(username="camponotus", password="pass")
        rendered = user_avatar(user, size=32)
        self.assertIn("user-avatar-placeholder", rendered)
        self.assertIn("C", rendered)
        self.assertIn('title="@camponotus"', rendered)

        # Anonymous user
        rendered_anon = user_avatar(None, size=24)
        self.assertIn("bi-person-fill", rendered_anon)


class UserProfileSettingsViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="settingsuser", password="secretpassword", first_name="OldFirst"
        )
        self.url = reverse("user_profile_settings")

    def test_requires_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_get_settings_page(self):
        self.client.login(username="settingsuser", password="secretpassword")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Profile & Avatar")
        self.assertContains(response, "Email Settings")
        self.assertContains(response, "Password & Security")
        self.assertContains(response, "OldFirst")

    def test_post_update_profile_text_fields(self):
        self.client.login(username="settingsuser", password="secretpassword")
        data = {
            "first_name": "NewFirst",
            "last_name": "NewLast",
            "bio": "I keep Lasius flavus and Messor barbarus.",
            "location": "Munich, Germany",
        }
        response = self.client.post(self.url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "NewFirst")
        self.assertEqual(self.user.last_name, "NewLast")
        self.assertEqual(self.user.profile.bio, "I keep Lasius flavus and Messor barbarus.")
        self.assertEqual(self.user.profile.location, "Munich, Germany")

    def test_post_avatar_upload_and_delete(self):
        self.client.login(username="settingsuser", password="secretpassword")
        test_img = _create_test_image("PNG")
        data = {
            "first_name": "AntKeeper",
            "last_name": "Pro",
            "avatar": test_img,
        }
        response = self.client.post(self.url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.user.profile.refresh_from_db()
        self.assertTrue(bool(self.user.profile.avatar))
        self.assertIn("avatars/", self.user.profile.avatar.name)

        # Test avatar delete endpoint
        del_url = reverse("user_profile_avatar_delete")
        del_resp = self.client.post(del_url, follow=True)
        self.assertEqual(del_resp.status_code, 200)
        self.user.profile.refresh_from_db()
        self.assertFalse(bool(self.user.profile.avatar))

    def test_rejects_non_image_upload(self):
        self.client.login(username="settingsuser", password="secretpassword")
        fake_file = SimpleUploadedFile("script.sh", b"echo evil", content_type="text/x-shellscript")
        data = {
            "first_name": "Hacker",
            "avatar": fake_file,
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Upload a valid image", status_code=400)


class ProfileSubnavigationIntegrationTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="navuser", password="password123")
        self.client.login(username="navuser", password="password123")

    def test_subnav_present_on_all_pages(self):
        urls = [
            reverse("user_profile"),
            reverse("user_profile_colonies"),
            reverse("user_profile_journals"),
            reverse("user_profile_food_ratings"),
            reverse("user_profile_difficulty_ratings"),
            reverse("user_profile_settings"),
            reverse("account_email"),
            reverse("account_change_password"),
        ]
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "profile-subnav")
                self.assertContains(response, reverse("user_profile"))
                self.assertContains(response, reverse("user_profile_colonies"))
                self.assertContains(response, reverse("user_profile_settings"))


class UserProfilePrivacySettingsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="secretkeeper",
            password="secretpassword",
            first_name="Max",
            last_name="Mustermann",
        )
        self.profile = self.user.profile
        self.profile.location = "Hamburg, Germany"
        self.profile.bio = "Private antkeeper bio"
        self.profile.save()

    def test_default_privacy_values(self):
        self.assertFalse(self.profile.show_full_name)
        self.assertTrue(self.profile.show_location)
        self.assertTrue(self.profile.show_bio)
        # Default display name is always nickname
        self.assertEqual(self.profile.display_name, "@secretkeeper")

    def test_show_full_name_when_enabled(self):
        self.profile.show_full_name = True
        self.profile.save()
        self.assertEqual(self.profile.display_name, "Max Mustermann")

    def test_public_colonies_page_hides_real_name_by_default(self):
        colony_url = reverse("user_colonies", kwargs={"username": self.user.username})
        resp = self.client.get(colony_url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "@secretkeeper")
        self.assertNotContains(resp, "Max Mustermann")
        # Location is shown by default
        self.assertContains(resp, "Hamburg, Germany")
        self.assertContains(resp, "Private antkeeper bio")

        # Now enable full name and disable location/bio
        self.profile.show_full_name = True
        self.profile.show_location = False
        self.profile.show_bio = False
        self.profile.save()

        resp2 = self.client.get(colony_url)
        self.assertContains(resp2, "Max Mustermann")
        self.assertNotContains(resp2, "Hamburg, Germany")
        self.assertNotContains(resp2, "Private antkeeper bio")

    def test_settings_form_can_toggle_privacy(self):
        self.client.login(username="secretkeeper", password="secretpassword")
        settings_url = reverse("user_profile_settings")

        data = {
            "first_name": "Max",
            "last_name": "Mustermann",
            "bio": "Updated bio",
            "location": "Berlin",
            "show_full_name": "on",
            "show_location": "",  # unchecked
            "show_bio": "on",
        }
        resp = self.client.post(settings_url, data, follow=True)
        self.assertEqual(resp.status_code, 200)

        self.profile.refresh_from_db()
        self.assertTrue(self.profile.show_full_name)
        self.assertFalse(self.profile.show_location)
        self.assertTrue(self.profile.show_bio)
