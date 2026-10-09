import datetime
import os

from django import forms
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from django.core.exceptions import ValidationError
from ants.models import (
    AntSpecies,
    Colony,
    ColonyCareEvent,
    ColonyCensus,
    ColonyJournalEntry,
    ColonyJournalEntryImage,
    FoodItem,
    Genus,
)
from ants.utils.partial_date import (
    DAY,
    MONTH,
    YEAR,
    PartialDateField,
    format_partial_date,
)

# 1x1 transparent PNG, small enough to embed inline for upload tests.
_PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _make_species(name="Lasius niger", slug="lasius-niger"):
    genus = Genus.objects.create(name=name.split()[0])
    return AntSpecies.objects.create(name=name, valid=True, genus=genus, slug=slug)


def _png_upload(name="photo.png"):
    return SimpleUploadedFile(name, _PNG_BYTES, content_type="image/png")


class ColonyModelTest(TestCase):
    def setUp(self):
        self.species = _make_species()
        self.user = User.objects.create_user(username="tester", password="pass")

    def test_slug_generated_from_name(self):
        colony = Colony.objects.create(user=self.user, species=self.species, name="My First Colony")
        self.assertEqual(colony.slug, "my-first-colony")

    def test_slug_collision_within_same_user_gets_suffixed(self):
        Colony.objects.create(user=self.user, species=self.species, name="Empire")
        second = Colony.objects.create(user=self.user, species=self.species, name="Empire!!")
        # slugify("Empire") == slugify("Empire!!") == "empire" -- must not collide
        self.assertEqual(second.slug, "empire-2")

    def test_name_unique_per_user(self):
        Colony.objects.create(user=self.user, species=self.species, name="Ants")
        with self.assertRaises(IntegrityError):
            Colony.objects.create(user=self.user, species=self.species, name="Ants")

    def test_different_users_can_share_a_name(self):
        other = User.objects.create_user(username="other", password="pass")
        Colony.objects.create(user=self.user, species=self.species, name="Ants")
        Colony.objects.create(user=other, species=self.species, name="Ants")
        self.assertEqual(Colony.objects.filter(name="Ants").count(), 2)

    def test_status_changed_at_stamped_on_creation(self):
        colony = Colony.objects.create(user=self.user, species=self.species, name="Ants")
        self.assertEqual(colony.status_changed_at, timezone.now().date())

    def test_status_changed_at_untouched_when_status_unchanged(self):
        colony = Colony.objects.create(user=self.user, species=self.species, name="Ants")
        colony.status_changed_at = datetime.date(2020, 1, 1)
        colony.save(update_fields=["status_changed_at"])
        colony.name = "Ants (renamed)"
        colony.save()
        self.assertEqual(colony.status_changed_at, datetime.date(2020, 1, 1))

    def test_status_changed_at_updated_on_status_change(self):
        colony = Colony.objects.create(user=self.user, species=self.species, name="Ants")
        colony.status_changed_at = datetime.date(2020, 1, 1)
        colony.save(update_fields=["status_changed_at"])
        colony.status = Colony.DEAD
        colony.save()
        self.assertEqual(colony.status_changed_at, timezone.now().date())

    def test_is_visible_publicly(self):
        colony = Colony.objects.create(user=self.user, species=self.species, name="Ants", is_public=True)
        self.assertTrue(colony.is_visible_publicly)
        colony.force_private_by_staff = True
        colony.save()
        self.assertFalse(colony.is_visible_publicly)


class ColonyCreateViewTest(TestCase):
    def setUp(self):
        self.species = _make_species()
        self.url = reverse("colony_create")
        self.user = User.objects.create_user(username="tester", password="pass")

    def test_anonymous_redirects_to_login(self):
        response = self.client.post(self.url, {"species": self.species.pk, "name": "Ants"})
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/", response["Location"])
        self.assertFalse(Colony.objects.exists())

    def test_logged_in_creates_colony(self):
        self.client.login(username="tester", password="pass")
        response = self.client.post(self.url, {"species": self.species.pk, "name": "Ants"})
        colony = Colony.objects.get(user=self.user)
        self.assertRedirects(response, colony.get_absolute_url())
        self.assertEqual(colony.species, self.species)

    def test_duplicate_name_shows_form_error_not_500(self):
        Colony.objects.create(user=self.user, species=self.species, name="Ants")
        self.client.login(username="tester", password="pass")
        response = self.client.post(self.url, {"species": self.species.pk, "name": "Ants"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Colony.objects.filter(user=self.user).count(), 1)

    def test_title_image_upload(self):
        self.client.login(username="tester", password="pass")
        response = self.client.post(
            self.url,
            {"species": self.species.pk, "name": "Ants", "title_image": _png_upload()},
        )
        colony = Colony.objects.get(user=self.user)
        self.assertRedirects(response, colony.get_absolute_url())
        self.assertTrue(hasattr(colony, "title_image"))

    def test_invalid_title_image_does_not_break_creation(self):
        self.client.login(username="tester", password="pass")
        bogus = SimpleUploadedFile("not-an-image.png", b"not a real image", content_type="image/png")
        response = self.client.post(
            self.url,
            {"species": self.species.pk, "name": "Ants", "title_image": bogus},
        )
        colony = Colony.objects.get(user=self.user)
        self.assertRedirects(response, colony.get_absolute_url())
        self.assertFalse(hasattr(colony, "title_image"))

    def test_rate_limit_blocks_after_max_creations_in_window(self):
        from ants.views import ColonyCreateView

        self.client.login(username="tester", password="pass")
        for i in range(ColonyCreateView.MAX_CREATIONS_PER_WINDOW):
            response = self.client.post(self.url, {"species": self.species.pk, "name": f"Colony {i}"})
            self.assertEqual(response.status_code, 302)
        self.assertEqual(
            Colony.objects.filter(user=self.user).count(), ColonyCreateView.MAX_CREATIONS_PER_WINDOW
        )

        response = self.client.post(self.url, {"species": self.species.pk, "name": "One too many"})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Colony.objects.filter(name="One too many").exists())


class ColonyOwnershipTest(TestCase):
    """Edit/delete/status/visibility/journal endpoints must never touch another user's colony."""

    def setUp(self):
        self.species = _make_species()
        self.owner = User.objects.create_user(username="owner", password="pass")
        self.intruder = User.objects.create_user(username="intruder", password="pass")
        self.colony = Colony.objects.create(user=self.owner, species=self.species, name="Ants")

    def test_edit_by_non_owner_404s(self):
        self.client.login(username="intruder", password="pass")
        response = self.client.get(reverse("colony_edit", args=[self.colony.pk]))
        self.assertEqual(response.status_code, 404)

    def test_delete_by_non_owner_404s(self):
        self.client.login(username="intruder", password="pass")
        response = self.client.post(reverse("colony_delete", args=[self.colony.pk]))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Colony.objects.filter(pk=self.colony.pk).exists())

    def test_status_update_by_non_owner_404s(self):
        self.client.login(username="intruder", password="pass")
        response = self.client.post(
            reverse("colony_status_update", args=[self.colony.pk]), {"status": Colony.DEAD}
        )
        self.assertEqual(response.status_code, 404)
        self.colony.refresh_from_db()
        self.assertEqual(self.colony.status, Colony.ACTIVE)

    def test_visibility_update_by_non_owner_404s(self):
        self.client.login(username="intruder", password="pass")
        response = self.client.post(
            reverse("colony_visibility_update", args=[self.colony.pk]), {"keep_private": "on"}
        )
        self.assertEqual(response.status_code, 404)
        self.colony.refresh_from_db()
        self.assertTrue(self.colony.is_public)

    def test_journal_entry_create_by_non_owner_404s(self):
        self.client.login(username="intruder", password="pass")
        response = self.client.post(
            reverse("colony_journal_entry_create", args=[self.colony.pk]),
            {"date": "2026-01-01", "note": "Sneaky entry"},
        )
        self.assertEqual(response.status_code, 404)
        self.assertFalse(self.colony.journal_entries.exists())

    def test_species_field_disabled_on_edit(self):
        other_species = _make_species(name="Formica rufa", slug="formica-rufa")
        self.client.login(username="owner", password="pass")
        response = self.client.post(
            reverse("colony_edit", args=[self.colony.pk]),
            {"species": other_species.pk, "name": "Ants renamed"},
        )
        self.assertEqual(response.status_code, 302)
        self.colony.refresh_from_db()
        self.assertEqual(self.colony.species, self.species)
        self.assertEqual(self.colony.name, "Ants renamed")


class ColonyDeleteViewTest(TestCase):
    def setUp(self):
        self.species = _make_species()
        self.user = User.objects.create_user(username="tester", password="pass")
        self.colony = Colony.objects.create(user=self.user, species=self.species, name="Ants")

    def test_owner_can_delete_with_matching_name(self):
        self.client.login(username="tester", password="pass")
        response = self.client.post(
            reverse("colony_delete", args=[self.colony.pk]),
            {"confirm_colony_name": "Ants"},
        )
        self.assertRedirects(response, reverse("user_profile"))
        self.assertFalse(Colony.objects.filter(pk=self.colony.pk).exists())

    def test_owner_cannot_delete_with_wrong_name(self):
        self.client.login(username="tester", password="pass")
        response = self.client.post(
            reverse("colony_delete", args=[self.colony.pk]),
            {"confirm_colony_name": "Wrong Name"},
        )
        self.assertRedirects(response, self.colony.get_absolute_url())
        self.assertTrue(Colony.objects.filter(pk=self.colony.pk).exists())

    def test_delete_cascades_to_journal_entries_censuses_and_care_events(self):
        entry = ColonyJournalEntry.objects.create(colony=self.colony, date="2026-01-01", note="Hi")
        census = ColonyCensus.objects.create(colony=self.colony, date="2026-01-01", workers=50)
        care = ColonyCareEvent.objects.create(colony=self.colony, category=ColonyCareEvent.FEEDING)

        self.client.login(username="tester", password="pass")
        self.client.post(
            reverse("colony_delete", args=[self.colony.pk]),
            {"confirm_colony_name": "Ants"},
        )
        self.assertFalse(ColonyJournalEntry.objects.filter(pk=entry.pk).exists())
        self.assertFalse(ColonyCensus.objects.filter(pk=census.pk).exists())
        self.assertFalse(ColonyCareEvent.objects.filter(pk=care.pk).exists())


class ColonyStatusAndVisibilityViewTest(TestCase):
    def setUp(self):
        self.species = _make_species()
        self.user = User.objects.create_user(username="tester", password="pass")
        self.colony = Colony.objects.create(user=self.user, species=self.species, name="Ants")
        self.client.login(username="tester", password="pass")

    def test_valid_status_update(self):
        response = self.client.post(
            reverse("colony_status_update", args=[self.colony.pk]), {"status": Colony.GIVEN_AWAY}
        )
        self.assertRedirects(response, self.colony.get_absolute_url())
        self.colony.refresh_from_db()
        self.assertEqual(self.colony.status, Colony.GIVEN_AWAY)

    def test_invalid_status_returns_400(self):
        response = self.client.post(
            reverse("colony_status_update", args=[self.colony.pk]), {"status": "NOT_A_STATUS"}
        )
        self.assertEqual(response.status_code, 400)

    def test_visibility_toggle_to_private(self):
        response = self.client.post(
            reverse("colony_visibility_update", args=[self.colony.pk]),
            {"keep_private": "on", "hide_found_location": "on"},
        )
        self.assertRedirects(response, self.colony.get_absolute_url())
        self.colony.refresh_from_db()
        self.assertFalse(self.colony.is_public)
        self.assertFalse(self.colony.share_found_location)

    def test_visibility_stays_public_when_boxes_unchecked(self):
        # Colonies are public by default -- an empty POST (nothing checked)
        # must leave them public, not flip them private.
        response = self.client.post(reverse("colony_visibility_update", args=[self.colony.pk]), {})
        self.assertRedirects(response, self.colony.get_absolute_url())
        self.colony.refresh_from_db()
        self.assertTrue(self.colony.is_public)
        self.assertTrue(self.colony.share_found_location)


class ColonyJournalEntryViewTest(TestCase):
    def setUp(self):
        self.species = _make_species()
        self.user = User.objects.create_user(username="tester", password="pass")
        self.colony = Colony.objects.create(user=self.user, species=self.species, name="Ants")
        self.client.login(username="tester", password="pass")

    def test_create_entry_without_photo(self):
        response = self.client.post(
            reverse("colony_journal_entry_create", args=[self.colony.pk]),
            {"date": "2026-01-01", "note": "First workers spotted."},
        )
        self.assertRedirects(response, self.colony.get_absolute_url())
        entry = self.colony.journal_entries.get()
        self.assertEqual(entry.note, "First workers spotted.")
        self.assertEqual(entry.images.count(), 0)

    def test_create_entry_with_multiple_photos(self):
        response = self.client.post(
            reverse("colony_journal_entry_create", args=[self.colony.pk]),
            {
                "date": "2026-01-01",
                "note": "Growing fast.",
                "images": [_png_upload("a.png"), _png_upload("b.png")],
            },
        )
        self.assertRedirects(response, self.colony.get_absolute_url())
        entry = self.colony.journal_entries.get()
        self.assertEqual(entry.images.count(), 2)

    def test_invalid_entry_not_created(self):
        response = self.client.post(
            reverse("colony_journal_entry_create", args=[self.colony.pk]),
            {"date": "", "note": ""},
        )
        self.assertRedirects(response, self.colony.get_absolute_url())
        self.assertFalse(self.colony.journal_entries.exists())

    def test_delete_entry(self):
        entry = ColonyJournalEntry.objects.create(colony=self.colony, date="2026-01-01", note="Hi")
        response = self.client.post(
            reverse("colony_journal_entry_delete", args=[self.colony.pk, entry.pk])
        )
        self.assertRedirects(response, self.colony.get_absolute_url())
        self.assertFalse(ColonyJournalEntry.objects.filter(pk=entry.pk).exists())

    def test_edit_appends_photos_to_existing_entry(self):
        entry = ColonyJournalEntry.objects.create(colony=self.colony, date="2026-01-01", note="Hi")
        existing = ColonyJournalEntryImage.objects.create(
            journal_entry=entry, image_file=_png_upload("a.png"), ordering=0
        )
        response = self.client.post(
            reverse("colony_journal_entry_edit", args=[self.colony.pk, entry.pk]),
            {
                "date": "2026-01-01",
                "note": "Hi (updated)",
                "existing_image": [existing.pk],
                "images": [_png_upload("b.png")],
            },
        )
        self.assertRedirects(response, self.colony.get_absolute_url())
        entry.refresh_from_db()
        self.assertEqual(entry.note, "Hi (updated)")
        self.assertEqual(entry.images.count(), 2)

    def test_date_differs_from_created_property(self):
        today = timezone.localdate()
        entry_same = ColonyJournalEntry.objects.create(
            colony=self.colony, date=today, note="Today entry"
        )
        self.assertFalse(entry_same.date_differs_from_created)

        entry_backdated = ColonyJournalEntry.objects.create(
            colony=self.colony,
            date=today - datetime.timedelta(days=365),
            note="Old entry",
        )
        self.assertTrue(entry_backdated.date_differs_from_created)

    def test_colony_detail_journal_sorting(self):
        today = timezone.localdate()
        entry1 = ColonyJournalEntry.objects.create(
            colony=self.colony, date=today, note="Entry Newer Date"
        )
        entry2 = ColonyJournalEntry.objects.create(
            colony=self.colony,
            date=today - datetime.timedelta(days=100),
            note="Entry Older Date Backdated",
        )
        resp_date = self.client.get(self.colony.get_absolute_url())
        entries_date = list(resp_date.context["journal_entries"])
        self.assertEqual(entries_date, [entry1, entry2])

        resp_created = self.client.get(
            self.colony.get_absolute_url(), {"journal_sort": "created"}
        )
        entries_created = list(resp_created.context["journal_entries"])
        self.assertEqual(entries_created, [entry2, entry1])


class ColonyJournalEntryImageManagementTest(TestCase):
    """Existing photos are reordered/removed client-side and only applied
    when the entry's edit form (colony_journal_entry_edit) is submitted."""

    def setUp(self):
        self.species = _make_species()
        self.owner = User.objects.create_user(username="owner", password="pass")
        self.intruder = User.objects.create_user(username="intruder", password="pass")
        self.colony = Colony.objects.create(user=self.owner, species=self.species, name="Ants")
        self.entry = ColonyJournalEntry.objects.create(colony=self.colony, date="2026-01-01", note="Hi")
        self.img1 = ColonyJournalEntryImage.objects.create(
            journal_entry=self.entry, image_file=_png_upload("a.png"), ordering=0
        )
        self.img2 = ColonyJournalEntryImage.objects.create(
            journal_entry=self.entry, image_file=_png_upload("b.png"), ordering=1
        )
        self.img3 = ColonyJournalEntryImage.objects.create(
            journal_entry=self.entry, image_file=_png_upload("c.png"), ordering=2
        )
        self.url = reverse("colony_journal_entry_edit", args=[self.colony.pk, self.entry.pk])
        self.base_data = {"date": "2026-01-01", "note": "Hi"}

    def test_reordering_existing_photos(self):
        self.client.login(username="owner", password="pass")
        response = self.client.post(
            self.url,
            {**self.base_data, "existing_image": [self.img2.pk, self.img1.pk, self.img3.pk]},
        )
        self.assertRedirects(response, self.colony.get_absolute_url())
        ordered = list(self.entry.images.all())
        self.assertEqual([im.pk for im in ordered], [self.img2.pk, self.img1.pk, self.img3.pk])

    def test_omitting_an_existing_photo_deletes_it(self):
        self.client.login(username="owner", password="pass")
        response = self.client.post(
            self.url,
            {**self.base_data, "existing_image": [self.img1.pk, self.img3.pk]},
        )
        self.assertRedirects(response, self.colony.get_absolute_url())
        self.assertFalse(ColonyJournalEntryImage.objects.filter(pk=self.img2.pk).exists())
        ordered = list(self.entry.images.all())
        self.assertEqual([im.pk for im in ordered], [self.img1.pk, self.img3.pk])

    def test_omitting_an_existing_photo_deletes_its_file_from_storage(self):
        self.client.login(username="owner", password="pass")
        file_path = self.img2.image_file.path
        self.assertTrue(os.path.exists(file_path))
        self.client.post(
            self.url,
            {**self.base_data, "existing_image": [self.img1.pk, self.img3.pk]},
        )
        self.assertFalse(os.path.exists(file_path))

    def test_omitting_existing_image_field_entirely_removes_all_photos(self):
        self.client.login(username="owner", password="pass")
        response = self.client.post(self.url, self.base_data)
        self.assertRedirects(response, self.colony.get_absolute_url())
        self.assertEqual(self.entry.images.count(), 0)

    def test_new_photos_are_appended_after_kept_existing_ones(self):
        self.client.login(username="owner", password="pass")
        response = self.client.post(
            self.url,
            {
                **self.base_data,
                "existing_image": [self.img3.pk, self.img1.pk],
                "images": [_png_upload("d.png")],
            },
        )
        self.assertRedirects(response, self.colony.get_absolute_url())
        ordered = list(self.entry.images.all())
        self.assertEqual(ordered[0].pk, self.img3.pk)
        self.assertEqual(ordered[1].pk, self.img1.pk)
        self.assertEqual(len(ordered), 3)
        self.assertNotIn(self.img2.pk, [im.pk for im in ordered])

    def test_non_owner_cannot_reorder_or_remove_photos(self):
        self.client.login(username="intruder", password="pass")
        response = self.client.post(
            self.url, {**self.base_data, "existing_image": [self.img1.pk]}
        )
        self.assertEqual(response.status_code, 404)
        ordered = list(self.entry.images.all())
        self.assertEqual([im.pk for im in ordered], [self.img1.pk, self.img2.pk, self.img3.pk])


class ColonyDetailViewTest(TestCase):
    def setUp(self):
        self.species = _make_species()
        self.owner = User.objects.create_user(username="owner", password="pass")
        self.other = User.objects.create_user(username="other", password="pass")
        self.colony = Colony.objects.create(user=self.owner, species=self.species, name="Ants")

    def _url(self):
        return reverse("colony_detail", args=[self.owner.username, self.colony.slug])

    def test_colony_is_public_by_default(self):
        self.assertTrue(self.colony.is_public)
        self.assertTrue(self.colony.share_found_location)

    def test_public_colony_visible_to_anonymous(self):
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 200)

    def test_private_colony_404s_for_anonymous(self):
        self.colony.is_public = False
        self.colony.save()
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 404)

    def test_private_colony_404s_for_other_user(self):
        self.colony.is_public = False
        self.colony.save()
        self.client.login(username="other", password="pass")
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 404)

    def test_private_colony_visible_to_owner(self):
        self.colony.is_public = False
        self.colony.save()
        self.client.login(username="owner", password="pass")
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 200)

    def test_force_private_by_staff_overrides_public_flag(self):
        self.colony.force_private_by_staff = True
        self.colony.save()
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 404)

    def test_force_private_still_visible_to_owner(self):
        self.colony.force_private_by_staff = True
        self.colony.save()
        self.client.login(username="owner", password="pass")
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 200)

    def test_found_location_shown_by_default(self):
        self.colony.found_location = "Secret Forest"
        self.colony.save()
        response = self.client.get(self._url())
        self.assertContains(response, "Secret Forest")

    def test_found_location_hidden_when_opted_out(self):
        self.colony.found_location = "Secret Forest"
        self.colony.share_found_location = False
        self.colony.save()
        response = self.client.get(self._url())
        self.assertNotContains(response, "Secret Forest")

    def test_purchase_info_never_shown_publicly(self):
        self.colony.purchase_shop = "Ant Shop XYZ"
        self.colony.save()
        response = self.client.get(self._url())
        self.assertNotContains(response, "Ant Shop XYZ")

    def test_username_matching_is_case_insensitive(self):
        url = reverse("colony_detail", args=[self.owner.username.upper(), self.colony.slug])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_page_is_never_cached(self):
        # Otherwise the site-wide 1-hour page cache (CACHE_MIDDLEWARE_SECONDS)
        # would serve stale journal updates -- or worse, one user's cached
        # owner-only view to someone else requesting the same URL.
        response = self.client.get(self._url())
        self.assertIn("no-cache", response["Cache-Control"])


class PartialDateFieldTest(TestCase):
    def setUp(self):
        self.field = PartialDateField()

    def test_nothing_entered_is_none(self):
        self.assertIsNone(self.field.clean(["", "", ""]))

    def test_year_only(self):
        value, precision = self.field.clean(["2022", "", ""])
        self.assertEqual(value, datetime.date(2022, 1, 1))
        self.assertEqual(precision, YEAR)

    def test_year_and_month(self):
        value, precision = self.field.clean(["2022", "6", ""])
        self.assertEqual(value, datetime.date(2022, 6, 1))
        self.assertEqual(precision, MONTH)

    def test_full_date(self):
        value, precision = self.field.clean(["2022", "6", "15"])
        self.assertEqual(value, datetime.date(2022, 6, 15))
        self.assertEqual(precision, DAY)

    def test_day_without_month_is_invalid(self):
        with self.assertRaises(forms.ValidationError):
            self.field.clean(["2022", "", "15"])

    def test_month_or_day_without_year_is_invalid(self):
        with self.assertRaises(forms.ValidationError):
            self.field.clean(["", "6", ""])

    def test_invalid_day_for_month_is_invalid(self):
        with self.assertRaises(forms.ValidationError):
            self.field.clean(["2022", "2", "30"])  # Feb 30 doesn't exist

    def test_feb_29_rejected_outside_leap_year(self):
        with self.assertRaises(forms.ValidationError):
            self.field.clean(["2023", "2", "29"])  # 2023 is not a leap year

    def test_feb_29_accepted_in_leap_year(self):
        value, precision = self.field.clean(["2024", "2", "29"])
        self.assertEqual(value, datetime.date(2024, 2, 29))
        self.assertEqual(precision, DAY)


class FormatPartialDateTest(TestCase):
    def test_year_precision(self):
        self.assertEqual(format_partial_date(datetime.date(2022, 6, 15), YEAR), "2022")

    def test_month_precision(self):
        self.assertEqual(format_partial_date(datetime.date(2022, 6, 15), MONTH), "June 2022")

    def test_day_precision(self):
        self.assertEqual(format_partial_date(datetime.date(2022, 6, 15), DAY), "June 15, 2022")

    def test_no_date(self):
        self.assertEqual(format_partial_date(None, YEAR), "")


class ColonyPartialDateViewTest(TestCase):
    def setUp(self):
        self.species = _make_species()
        self.user = User.objects.create_user(username="tester", password="pass")
        self.url = reverse("colony_create")
        self.client.login(username="tester", password="pass")

    def test_create_with_year_only_found_date(self):
        response = self.client.post(
            self.url,
            {
                "species": self.species.pk, "name": "Ants",
                "found_date_0": "2020", "found_date_1": "", "found_date_2": "",
                "purchase_date_0": "", "purchase_date_1": "", "purchase_date_2": "",
            },
        )
        colony = Colony.objects.get(user=self.user)
        self.assertRedirects(response, colony.get_absolute_url())
        self.assertEqual(colony.found_date, datetime.date(2020, 1, 1))
        self.assertEqual(colony.found_date_precision, YEAR)

    def test_create_with_full_purchase_date(self):
        response = self.client.post(
            self.url,
            {
                "species": self.species.pk, "name": "Ants",
                "found_date_0": "", "found_date_1": "", "found_date_2": "",
                "purchase_date_0": "2021", "purchase_date_1": "3", "purchase_date_2": "10",
            },
        )
        colony = Colony.objects.get(user=self.user)
        self.assertRedirects(response, colony.get_absolute_url())
        self.assertEqual(colony.purchase_date, datetime.date(2021, 3, 10))
        self.assertEqual(colony.purchase_date_precision, DAY)

    def test_create_with_no_dates(self):
        response = self.client.post(self.url, {"species": self.species.pk, "name": "Ants"})
        colony = Colony.objects.get(user=self.user)
        self.assertRedirects(response, colony.get_absolute_url())
        self.assertIsNone(colony.found_date)
        self.assertEqual(colony.found_date_precision, "")

    def test_day_without_month_shows_form_error(self):
        response = self.client.post(
            self.url,
            {
                "species": self.species.pk, "name": "Ants",
                "found_date_0": "2020", "found_date_1": "", "found_date_2": "15",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Colony.objects.filter(user=self.user).exists())

    def test_detail_page_shows_year_only_display(self):
        self.client.post(
            self.url,
            {
                "species": self.species.pk, "name": "Ants",
                "found_date_0": "2020", "found_date_1": "", "found_date_2": "",
            },
        )
        colony = Colony.objects.get(user=self.user)
        response = self.client.get(colony.get_absolute_url())
        self.assertContains(response, "2020")
        self.assertNotContains(response, "January 1, 2020")

    def test_edit_prefills_existing_partial_date(self):
        colony = Colony.objects.create(
            user=self.user, species=self.species, name="Ants",
            found_date=datetime.date(2019, 5, 1), found_date_precision=MONTH,
        )
        response = self.client.get(reverse("colony_edit", args=[colony.pk]))
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertEqual(form.fields["found_date"].initial, (datetime.date(2019, 5, 1), MONTH))


class CommunityJournalViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="keeper", password="pass")
        self.other_user = User.objects.create_user(username="other_keeper", password="pass")
        self.lasius = _make_species(name="Lasius niger", slug="lasius-niger")
        self.formica = _make_species(name="Formica rufa", slug="formica-rufa")

        self.public_colony = Colony.objects.create(
            user=self.user, species=self.lasius, name="Public Ants", is_public=True
        )
        self.private_colony = Colony.objects.create(
            user=self.user, species=self.lasius, name="Private Ants", is_public=False
        )
        self.hidden_colony = Colony.objects.create(
            user=self.other_user, species=self.formica, name="Hidden Ants",
            is_public=True, force_private_by_staff=True,
        )
        self.other_public_colony = Colony.objects.create(
            user=self.other_user, species=self.formica, name="Other Public Ants", is_public=True
        )

        self.public_entry = ColonyJournalEntry.objects.create(
            colony=self.public_colony, date="2026-01-01", note="Public update"
        )
        self.private_entry = ColonyJournalEntry.objects.create(
            colony=self.private_colony, date="2026-01-02", note="Private update"
        )
        self.hidden_entry = ColonyJournalEntry.objects.create(
            colony=self.hidden_colony, date="2026-01-03", note="Staff-hidden update"
        )
        self.other_public_entry = ColonyJournalEntry.objects.create(
            colony=self.other_public_colony, date="2026-01-04", note="Other public update"
        )

    def test_page_loads_for_anonymous(self):
        response = self.client.get(reverse("community_journal"))
        self.assertEqual(response.status_code, 200)

    def test_page_and_results_are_never_cached(self):
        # Otherwise the site-wide 1-hour page cache (CACHE_MIDDLEWARE_SECONDS)
        # would keep serving a stale feed after new journal entries are added.
        response = self.client.get(reverse("community_journal"))
        self.assertIn("no-cache", response["Cache-Control"])
        results = self.client.get(reverse("community_journal_results"))
        self.assertIn("no-cache", results["Cache-Control"])

    def test_results_only_show_visible_public_entries(self):
        response = self.client.get(reverse("community_journal_results"))
        self.assertContains(response, "Public update")
        self.assertContains(response, "Other public update")
        self.assertNotContains(response, "Private update")
        self.assertNotContains(response, "Staff-hidden update")

    def test_filter_options_exclude_private_colonies(self):
        response = self.client.get(reverse("community_journal"))
        usernames = list(response.context["usernames"])
        self.assertIn("keeper", usernames)
        self.assertIn("other_keeper", usernames)
        species_names = [s.name for s in response.context["species_list"]]
        self.assertIn("Lasius niger", species_names)
        self.assertIn("Formica rufa", species_names)

    def test_filter_by_species(self):
        response = self.client.get(reverse("community_journal_results"), {"species": "lasius-niger"})
        self.assertContains(response, "Public update")
        self.assertNotContains(response, "Other public update")

    def test_filter_by_genus(self):
        response = self.client.get(reverse("community_journal_results"), {"genus": "formica"})
        self.assertContains(response, "Other public update")
        self.assertNotContains(response, "Public update")

    def test_filter_by_user(self):
        response = self.client.get(reverse("community_journal_results"), {"user": "other_keeper"})
        self.assertContains(response, "Other public update")
        self.assertNotContains(response, "Public update")

    def test_filter_with_no_matches(self):
        response = self.client.get(reverse("community_journal_results"), {"user": "nobody"})
        self.assertContains(response, "No journal entries match")

    def test_pagination(self):
        from ants.views import CommunityJournalResultsView

        for i in range(CommunityJournalResultsView.RESULTS_PER_PAGE + 5):
            ColonyJournalEntry.objects.create(
                colony=self.public_colony, date="2026-02-01", note=f"Bulk entry {i}"
            )
        response = self.client.get(reverse("community_journal_results"))
        self.assertContains(response, 'aria-label="Pagination"')
        page2 = self.client.get(reverse("community_journal_results"), {"page": 2})
        self.assertEqual(page2.status_code, 200)

    def test_long_entry_shows_read_full_entry_link_to_colony_anchor(self):
        long_note = " ".join(f"word{i}" for i in range(50))
        entry = ColonyJournalEntry.objects.create(colony=self.public_colony, date="2026-03-01", note=long_note)
        response = self.client.get(reverse("community_journal_results"))
        expected_link = f"{self.public_colony.get_absolute_url()}#entry-{entry.pk}"
        self.assertContains(response, expected_link)
        self.assertContains(response, "Read full entry")

    def test_short_entry_has_no_read_full_entry_link(self):
        ColonyJournalEntry.objects.create(colony=self.public_colony, date="2026-03-01", note="Short note.")
        response = self.client.get(reverse("community_journal_results"))
        self.assertNotContains(response, "Read full entry")

    def test_colony_page_shows_full_untruncated_note_at_entry_anchor(self):
        long_note = " ".join(f"word{i}" for i in range(50))
        entry = ColonyJournalEntry.objects.create(colony=self.public_colony, date="2026-03-01", note=long_note)
        response = self.client.get(self.public_colony.get_absolute_url())
        self.assertContains(response, f'id="entry-{entry.pk}"')
        self.assertContains(response, long_note)

    def test_default_sort_is_recently_added_and_supports_sort_by_date(self):
        backdated_entry = ColonyJournalEntry.objects.create(
            colony=self.public_colony, date="2020-01-01", note="Retroactive update"
        )
        response = self.client.get(reverse("community_journal_results"))
        page_entries = list(response.context["page_obj"])
        self.assertEqual(page_entries[0], backdated_entry)

        response_date = self.client.get(reverse("community_journal_results"), {"sort": "date"})
        page_entries_date = list(response_date.context["page_obj"])
        self.assertEqual(page_entries_date[0], self.other_public_entry)
        self.assertEqual(page_entries_date[-1], backdated_entry)

    def test_backdated_entry_displays_added_date(self):
        today = timezone.localdate()
        ColonyJournalEntry.objects.create(
            colony=self.public_colony,
            date=today - datetime.timedelta(days=200),
            note="Backdated note",
        )
        response = self.client.get(reverse("community_journal_results"))
        self.assertContains(response, "Backdated note")
        self.assertContains(response, "added")


class ColonyCensusModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="censuskeeper", password="pw")
        self.species = _make_species()
        self.colony = Colony.objects.create(user=self.user, species=self.species, name="CensusColony")

    def test_census_creation_workers_only(self):
        census = ColonyCensus.objects.create(
            colony=self.colony,
            workers=42,
            workers_is_estimated=True,
            note="Counted via photo",
        )
        self.assertEqual(census.workers, 42)
        self.assertTrue(census.workers_is_estimated)
        self.assertIsNone(census.eggs)
        self.assertTrue(census.has_adult_counts)
        self.assertFalse(census.has_brood_counts)

    def test_census_creation_with_egg_clutches(self):
        census = ColonyCensus.objects.create(
            colony=self.colony,
            queens=1,
            workers=10,
            eggs=2,
            eggs_unit=ColonyCensus.UNIT_CLUTCHES,
            eggs_is_estimated=False,
            larvae=5,
            pupae=3,
        )
        self.assertEqual(census.eggs_unit, ColonyCensus.UNIT_CLUTCHES)
        self.assertTrue(census.has_adult_counts)
        self.assertTrue(census.has_brood_counts)

    def test_empty_census_raises_validation_error(self):
        census = ColonyCensus(colony=self.colony)
        with self.assertRaises(ValidationError):
            census.clean()


class ColonyCareEventModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="carekeeper", password="pw")
        self.species = _make_species()
        self.colony = Colony.objects.create(user=self.user, species=self.species, name="CareColony")
        self.food = FoodItem.objects.create(name="Honey water")

    def test_care_event_creation(self):
        event = ColonyCareEvent.objects.create(
            colony=self.colony,
            category=ColonyCareEvent.FEEDING,
            food_item=self.food,
            details="Fresh batch",
        )
        self.assertEqual(event.category, ColonyCareEvent.FEEDING)
        self.assertEqual(event.food_item.name, "Honey water")
        self.assertIn("Feeding", str(event))


class ColonyCensusAndCareViewsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="owner", password="pw")
        self.other_user = User.objects.create_user(username="intruder", password="pw")
        self.species = _make_species()
        self.colony = Colony.objects.create(user=self.user, species=self.species, name="MyColony")

    def test_owner_creates_census(self):
        self.client.force_login(self.user)
        url = reverse("colony_census_create", args=[self.colony.pk])
        response = self.client.post(url, {
            "date": "2026-04-01",
            "workers": 50,
            "workers_is_estimated": "on",
            "eggs": 2,
            "eggs_unit": "CLUTCHES",
            "note": "Growing fast",
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.colony.censuses.count(), 1)
        census = self.colony.censuses.first()
        self.assertEqual(census.workers, 50)
        self.assertTrue(census.workers_is_estimated)
        self.assertEqual(census.eggs, 2)
        self.assertEqual(census.eggs_unit, "CLUTCHES")

    def test_non_owner_cannot_create_census(self):
        self.client.force_login(self.other_user)
        url = reverse("colony_census_create", args=[self.colony.pk])
        response = self.client.post(url, {"date": "2026-04-01", "workers": 10})
        self.assertEqual(response.status_code, 404)

    def test_owner_deletes_census(self):
        census = ColonyCensus.objects.create(colony=self.colony, workers=15)
        self.client.force_login(self.user)
        url = reverse("colony_census_delete", args=[self.colony.pk, census.pk])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.colony.censuses.count(), 0)

    def test_non_owner_cannot_delete_census(self):
        census = ColonyCensus.objects.create(colony=self.colony, workers=15)
        self.client.force_login(self.other_user)
        url = reverse("colony_census_delete", args=[self.colony.pk, census.pk])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 404)

    def test_owner_creates_care_event(self):
        self.client.force_login(self.user)
        url = reverse("colony_care_event_create", args=[self.colony.pk])
        response = self.client.post(url, {
            "category": "HUMIDIFY",
            "date": "2026-04-01",
            "details": "Added 2ml water to nest",
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.colony.care_events.count(), 1)
        event = self.colony.care_events.first()
        self.assertEqual(event.category, "HUMIDIFY")

    def test_owner_deletes_care_event(self):
        event = ColonyCareEvent.objects.create(colony=self.colony, category="WATER")
        self.client.force_login(self.user)
        url = reverse("colony_care_event_delete", args=[self.colony.pk, event.pk])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.colony.care_events.count(), 0)

    def test_journal_entry_with_event_type(self):
        entry = ColonyJournalEntry.objects.create(
            colony=self.colony,
            date="2026-04-01",
            event_type=ColonyJournalEntry.EVENT_FIRST_WORKER,
            note="First worker emerged!",
        )
        self.assertEqual(entry.event_type, ColonyJournalEntry.EVENT_FIRST_WORKER)


    def test_census_chart_requires_at_least_two_worker_counts(self):
        # 1 census with workers, 1 census with only eggs -> chart should be None
        ColonyCensus.objects.create(colony=self.colony, date="2026-03-01", workers=10)
        ColonyCensus.objects.create(colony=self.colony, date="2026-04-01", eggs=20)
        self.client.force_login(self.user)
        response = self.client.get(self.colony.get_absolute_url())
        self.assertIsNone(response.context["census_chart_json"])

        # Add a 2nd census with workers -> chart should now be populated
        ColonyCensus.objects.create(colony=self.colony, date="2026-05-01", workers=30, workers_is_estimated=True)
        response2 = self.client.get(self.colony.get_absolute_url())
        self.assertIsNotNone(response2.context["census_chart_json"])
        self.assertIn('"workers": [10, 30]', response2.context["census_chart_json"])
        self.assertIn('"is_estimated": [false, true]', response2.context["census_chart_json"])

    def test_colony_create_prefill_from_species(self):
        self.client.force_login(self.user)
        url = reverse("colony_create") + f"?species={self.species.pk}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["species_name"], self.species.name)
        form = response.context["form"]
        self.assertEqual(form.initial.get("species"), self.species.pk)

    def test_species_detail_community_stats(self):
        # Create a journal entry for the public colony
        ColonyJournalEntry.objects.create(
            colony=self.colony,
            date="2026-04-01",
            note="Our public queen is doing great!",
        )
        url = reverse("ant_detail", args=[self.species.slug])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["community_colonies_count"], 1)
        self.assertEqual(response.context["community_journal_entries_count"], 1)

    def test_community_journal_filters_query_and_event_type(self):
        entry1 = ColonyJournalEntry.objects.create(
            colony=self.colony,
            date="2026-04-01",
            event_type=ColonyJournalEntry.EVENT_FIRST_WORKER,
            note="Exciting first worker emerged!",
        )
        entry2 = ColonyJournalEntry.objects.create(
            colony=self.colony,
            date="2026-04-02",
            event_type=ColonyJournalEntry.EVENT_NEST_MOVE,
            note="Moved into new Ytong nest.",
        )
        url = reverse("community_journal_results")

        # Test search q=
        resp_q = self.client.get(url + "?q=Ytong")
        self.assertEqual(resp_q.status_code, 200)
        entries = list(resp_q.context["page_obj"])
        self.assertIn(entry2, entries)
        self.assertNotIn(entry1, entries)

        # Test event_type filter
        resp_event = self.client.get(url + f"?event_type={ColonyJournalEntry.EVENT_FIRST_WORKER}")
        self.assertEqual(resp_event.status_code, 200)
        entries = list(resp_event.context["page_obj"])
        self.assertIn(entry1, entries)
        self.assertNotIn(entry2, entries)
