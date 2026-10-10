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
