import datetime
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from ants.models import (
    AntSpecies,
    Colony,
    ColonyJournalComment,
    ColonyJournalEntry,
    ColonyJournalEntryLike,
    Genus,
)



from django.core.files.uploadedfile import SimpleUploadedFile
from django.template import Context, Template
from ants.models import ColonyImage, ColonyJournalEntryImage

_PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _png_upload(name="photo.png"):
    return SimpleUploadedFile(name, _PNG_BYTES, content_type="image/png")

class ColonyJournalFeaturesTestCase(TestCase):
    def setUp(self):
        self.genus = Genus.objects.create(name="Camponotus")
        self.species = AntSpecies.objects.create(name="Camponotus ligniperda", genus=self.genus)

        self.alice = User.objects.create_user(username="alice", password="password123")
        self.bob = User.objects.create_user(username="bob", password="password123")
        self.admin = User.objects.create_user(username="admin_user", password="password123", is_staff=True)

        self.colony = Colony.objects.create(
            user=self.alice,
            species=self.species,
            name="My Wood Ants",
            is_public=True,
        )
        self.private_colony = Colony.objects.create(
            user=self.alice,
            species=self.species,
            name="Secret Ants",
            is_public=False,
        )

        self.entry = ColonyJournalEntry.objects.create(
            colony=self.colony,
            date=datetime.date(2026, 5, 12),
            note="First workers have emerged today!",
            event_type=ColonyJournalEntry.EVENT_FIRST_WORKER,
        )

        self.private_entry = ColonyJournalEntry.objects.create(
            colony=self.private_colony,
            date=datetime.date(2026, 5, 13),
            note="Private journal log.",
        )

    def test_user_colonies_view(self):
        url = reverse("user_colonies", args=["alice"])

        # Anonymous visitor sees only public colonies
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "My Wood Ants")
        self.assertNotContains(response, "Secret Ants")

        # Owner sees all colonies including private ones
        self.client.login(username="alice", password="password123")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Secret Ants")

        # Nonexistent user returns 404
        bad_url = reverse("user_colonies", args=["nonexistent_user"])
        response = self.client.get(bad_url)
        self.assertEqual(response.status_code, 404)

    def test_colony_journal_view(self):
        url = reverse("colony_journal", args=["alice", self.colony.slug])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "First workers have emerged today!")
        self.assertContains(response, "My Wood Ants")

        # Private colony access check
        private_url = reverse("colony_journal", args=["alice", self.private_colony.slug])
        self.client.logout()
        res_anon = self.client.get(private_url)
        self.assertEqual(res_anon.status_code, 404)

        self.client.login(username="bob", password="password123")
        res_stranger = self.client.get(private_url)
        self.assertEqual(res_stranger.status_code, 404)

        self.client.login(username="alice", password="password123")
        res_owner = self.client.get(private_url)
        self.assertEqual(res_owner.status_code, 200)

        self.client.login(username="admin_user", password="password123")
        res_admin = self.client.get(private_url)
        self.assertEqual(res_admin.status_code, 200)

    def test_colony_journal_entry_detail_and_short_redirect(self):
        canonical_url = self.entry.get_absolute_url()
        self.assertEqual(
            canonical_url,
            reverse("colony_journal_entry_detail", args=["alice", self.colony.slug, self.entry.pk]),
        )

        response = self.client.get(canonical_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "First workers have emerged today!")
        # Check breadcrumbs in HTML
        self.assertContains(response, "breadcrumb")
        self.assertContains(response, "@alice")

        # Short URL redirect test
        short_url = reverse("colony_journal_entry_short", args=[self.entry.pk])
        redirect_res = self.client.get(short_url)
        self.assertRedirects(redirect_res, canonical_url)

    def test_like_toggle(self):
        url = reverse("colony_journal_entry_like", args=[self.entry.pk])

        # Anonymous gets 401
        res_anon = self.client.post(url)
        self.assertEqual(res_anon.status_code, 401)
        self.assertEqual(ColonyJournalEntryLike.objects.filter(entry=self.entry).count(), 0)

        # Bob logs in and gives a heart
        self.client.login(username="bob", password="password123")
        res1 = self.client.post(url)
        self.assertEqual(res1.status_code, 200)
        self.assertEqual(ColonyJournalEntryLike.objects.filter(entry=self.entry).count(), 1)
        self.assertContains(res1, "bi-heart-fill")

        # Bob clicks again to remove the heart
        res2 = self.client.post(url)
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(ColonyJournalEntryLike.objects.filter(entry=self.entry).count(), 0)
        self.assertContains(res2, "bi-heart")

    def test_comment_create_and_delete(self):
        url = reverse("colony_journal_comment_create", args=[self.entry.pk])

        # Anonymous user cannot comment
        res_anon = self.client.post(url, {"comment": "Awesome queen!"})
        self.assertEqual(res_anon.status_code, 401)

        # Bob logs in and comments
        self.client.login(username="bob", password="password123")
        res_create = self.client.post(url, {"comment": "Congratulations on the nanitics!"})
        self.assertEqual(res_create.status_code, 302)
        comment = ColonyJournalComment.objects.filter(entry=self.entry, user=self.bob).first()
        self.assertIsNotNone(comment)
        self.assertEqual(comment.comment, "Congratulations on the nanitics!")
        self.assertFalse(comment.is_removed)

        # Bob can delete his own comment
        delete_url = reverse("colony_journal_comment_delete", args=[comment.pk])
        res_del = self.client.post(delete_url)
        self.assertEqual(res_del.status_code, 302)
        self.assertEqual(ColonyJournalComment.objects.filter(pk=comment.pk).count(), 0)

    def test_comment_moderation_spam_removal_and_staff_visibility(self):
        # Bob creates a spam comment
        comment = ColonyJournalComment.objects.create(
            entry=self.entry,
            user=self.bob,
            comment="Cheap crypto and spam link!",
        )

        detail_url = self.entry.get_absolute_url()
        mod_url = reverse("colony_journal_comment_moderate", args=[comment.pk])

        # Alice (regular user / colony owner) cannot moderate via staff endpoint
        self.client.login(username="alice", password="password123")
        res_non_staff = self.client.post(mod_url, {"action": "remove", "reason": "Spam"})
        self.assertEqual(res_non_staff.status_code, 403)

        # Admin marks comment as removed/spam
        self.client.login(username="admin_user", password="password123")
        res_mod = self.client.post(f"{mod_url}?action=remove&reason=Spam")
        self.assertEqual(res_mod.status_code, 302)

        comment.refresh_from_db()
        self.assertTrue(comment.is_removed)
        self.assertEqual(comment.removed_by, self.admin)
        self.assertEqual(comment.removal_reason, "Spam")

        # For normal users and guests: comment is COMPLETELY hidden
        self.client.logout()
        res_anon_detail = self.client.get(detail_url)
        self.assertNotContains(res_anon_detail, "Cheap crypto and spam link!")
        self.assertNotContains(res_anon_detail, "Removed by moderator")

        self.client.login(username="bob", password="password123")
        res_bob_detail = self.client.get(detail_url)
        self.assertNotContains(res_bob_detail, "Cheap crypto and spam link!")
        self.assertNotContains(res_bob_detail, "Removed by moderator")

        # For admin user: comment IS visible with moderator alert and reason
        self.client.login(username="admin_user", password="password123")
        res_admin_detail = self.client.get(detail_url)
        self.assertContains(res_admin_detail, "Removed by moderator")
        self.assertContains(res_admin_detail, "Cheap crypto and spam link!")
        self.assertContains(res_admin_detail, "Spam")

        # Admin can restore comment
        res_restore = self.client.post(f"{mod_url}?action=restore")
        self.assertEqual(res_restore.status_code, 302)
        comment.refresh_from_db()
        self.assertFalse(comment.is_removed)

        # Now regular users can see it again
        self.client.login(username="bob", password="password123")
        res_bob_again = self.client.get(detail_url)
        self.assertContains(res_bob_again, "Cheap crypto and spam link!")

    def test_community_journal_counter_annotations(self):
        # Add a heart and two comments (one active, one removed by admin)
        ColonyJournalEntryLike.objects.create(entry=self.entry, user=self.bob)
        ColonyJournalComment.objects.create(entry=self.entry, user=self.bob, comment="Nice ants!", is_removed=False)
        ColonyJournalComment.objects.create(entry=self.entry, user=self.bob, comment="Spam comment!", is_removed=True)

        comm_url = reverse("community_journal_results")
        self.client.login(username="bob", password="password123")
        response = self.client.get(comm_url)
        self.assertEqual(response.status_code, 200)

        # Heart count should be 1 and marked as active/liked
        self.assertContains(response, "bi-heart-fill")

        # Comment count should count ONLY non-removed comments (1 Comment, not 2)
        self.assertContains(response, ">1</span>")
        self.assertContains(response, "Comment")
        self.assertNotContains(response, ">2</span>")


    def test_social_cards_colony_detail_without_and_with_image(self):
        colony_url = self.colony.get_absolute_url()

        # 1. Without image: og:image and twitter:image should NOT be emitted
        res_no_img = self.client.get(colony_url)
        self.assertEqual(res_no_img.status_code, 200)
        self.assertContains(res_no_img, 'property="og:title" content="My Wood Ants (Camponotus ligniperda)')
        self.assertNotContains(res_no_img, 'property="og:image"')
        self.assertNotContains(res_no_img, 'name="twitter:image"')

        # 2. With image: og:image and twitter:image should point to the colony title image
        colony_img = ColonyImage.objects.create(colony=self.colony, image_file=_png_upload("colony.png"))
        res_with_img = self.client.get(colony_url)
        self.assertEqual(res_with_img.status_code, 200)
        self.assertContains(res_with_img, 'property="og:image"')
        self.assertContains(res_with_img, colony_img.image_file.url)
        self.assertContains(res_with_img, 'name="twitter:card" content="summary_large_image"')
        self.assertContains(res_with_img, 'name="twitter:image"')

    def test_social_cards_colony_journal_timeline(self):
        journal_url = reverse("colony_journal", args=[self.alice.username, self.colony.slug])

        # Without colony image: no og:image
        res_no_img = self.client.get(journal_url)
        self.assertEqual(res_no_img.status_code, 200)
        self.assertNotContains(res_no_img, 'property="og:image"')

        # With colony image: og:image present
        colony_img = ColonyImage.objects.create(colony=self.colony, image_file=_png_upload("colony.png"))
        res_with_img = self.client.get(journal_url)
        self.assertEqual(res_with_img.status_code, 200)
        self.assertContains(res_with_img, 'property="og:image"')
        self.assertContains(res_with_img, colony_img.image_file.url)
        self.assertContains(res_with_img, 'name="twitter:card" content="summary_large_image"')

    def test_social_cards_journal_entry_with_entry_photos(self):
        # Entry with 2 photos: should use the 1st photo
        img1 = ColonyJournalEntryImage.objects.create(
            journal_entry=self.entry, image_file=_png_upload("entry1.png"), ordering=0
        )
        img2 = ColonyJournalEntryImage.objects.create(
            journal_entry=self.entry, image_file=_png_upload("entry2.png"), ordering=1
        )
        self.assertEqual(self.entry.first_image, img1)

        detail_url = self.entry.get_absolute_url()
        res = self.client.get(detail_url)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'property="og:image"')
        self.assertContains(res, img1.image_file.url)
        self.assertNotContains(res, f'property="og:image" content="{img2.image_file.url}"')
        self.assertContains(res, 'name="twitter:card" content="summary_large_image"')

    def test_social_cards_journal_entry_fallback_and_no_image(self):
        detail_url = self.entry.get_absolute_url()

        # 1. Neither entry photo nor colony image: no og:image
        res_no_img = self.client.get(detail_url)
        self.assertEqual(res_no_img.status_code, 200)
        self.assertNotContains(res_no_img, 'property="og:image"')
        self.assertNotContains(res_no_img, 'name="twitter:image"')

        # 2. Colony image exists, entry has no photo: falls back to colony image
        colony_img = ColonyImage.objects.create(colony=self.colony, image_file=_png_upload("colony.png"))
        res_fallback = self.client.get(detail_url)
        self.assertEqual(res_fallback.status_code, 200)
        self.assertContains(res_fallback, 'property="og:image"')
        self.assertContains(res_fallback, colony_img.image_file.url)
        self.assertContains(res_fallback, 'name="twitter:card" content="summary_large_image"')

    def test_absolute_url_template_tag(self):
        t = Template("{% load ants %}{% absolute_url rel_url as out %}{{ out }}")
        rendered = t.render(Context({"rel_url": "/media/test.jpg"}))
        self.assertEqual(rendered, "/media/test.jpg")

        # When request is in context, builds full URI
        from django.test import RequestFactory
        factory = RequestFactory()
        req = factory.get("/some-page/")
        rendered_with_req = t.render(Context({"rel_url": "/media/test.jpg", "request": req}))
        self.assertEqual(rendered_with_req, "http://testserver/media/test.jpg")

        # When already absolute, returns unchanged
        rendered_abs = t.render(Context({"rel_url": "https://cdn.example.com/pic.jpg", "request": req}))
        self.assertEqual(rendered_abs, "https://cdn.example.com/pic.jpg")
