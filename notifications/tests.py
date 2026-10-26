from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from ants.models import (
    AntSpecies,
    Colony,
    ColonyJournalComment,
    ColonyJournalEntry,
    Genus,
)
from notifications.models import (
    EntrySubscription,
    Notification,
    NotificationKind,
    NotificationPreference,
)
from notifications.services import (
    handle_colony_forced_private,
    handle_comment_created,
    handle_comment_removed,
    handle_like_toggled,
    notify,
    parse_mentions,
)

User = get_user_model()


class NotificationModelAndServicesTests(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username="alice", password="password123")
        self.user2 = User.objects.create_user(username="bob", password="password123")
        self.user3 = User.objects.create_user(
            username="charlie", password="password123"
        )
        self.staff_user = User.objects.create_user(
            username="staff_mod", password="password123", is_staff=True
        )

        self.genus = Genus.objects.create(name="Lasius")
        self.species = AntSpecies.objects.create(
            name="Lasius niger",
            genus=self.genus,
        )

        self.public_colony = Colony.objects.create(
            user=self.user1,
            species=self.species,
            name="Alice Black Garden Ants",
            is_public=True,
        )

        self.private_colony = Colony.objects.create(
            user=self.user1,
            species=self.species,
            name="Alice Secret Colony",
            is_public=False,
        )

        self.public_entry = ColonyJournalEntry.objects.create(
            colony=self.public_colony,
            date="2026-03-01",
            note="Spring awakening!",
        )

        self.private_entry = ColonyJournalEntry.objects.create(
            colony=self.private_colony,
            date="2026-03-02",
            note="Secret queen laying eggs",
        )

    def test_prevent_self_notification(self):
        """User should not receive notification for their own action."""
        notif = notify(
            recipient=self.user1,
            kind=NotificationKind.ENTRY_LIKED,
            actor=self.user1,
            entry=self.public_entry,
        )
        self.assertIsNone(notif)
        self.assertEqual(Notification.objects.count(), 0)

    def test_disabled_preference_suppresses_in_app(self):
        """If user disabled in_app for a kind, notify() returns None."""
        NotificationPreference.objects.create(
            user=self.user1,
            kind=NotificationKind.ENTRY_LIKED,
            in_app=False,
        )
        notif = notify(
            recipient=self.user1,
            kind=NotificationKind.ENTRY_LIKED,
            actor=self.user2,
            entry=self.public_entry,
        )
        self.assertIsNone(notif)
        self.assertEqual(Notification.objects.filter(recipient=self.user1).count(), 0)

    def test_private_colony_visibility_check(self):
        """Unauthorized users shouldn't get alerts for private colonies."""
        notif = notify(
            recipient=self.user2,
            kind=NotificationKind.THREAD_REPLY,
            actor=self.user1,
            entry=self.private_entry,
        )
        self.assertIsNone(notif)

        # But Alice (owner) or staff can receive
        owner_notif = notify(
            recipient=self.user1,
            kind=NotificationKind.ENTRY_COMMENTED,
            actor=self.staff_user,
            entry=self.private_entry,
        )
        self.assertIsNotNone(owner_notif)

    def test_like_grouping_and_unliking(self):
        """Subsequent likes on the same entry group into one notification."""
        # Bob likes Alice's entry
        handle_like_toggled(self.public_entry, self.user2, liked=True)
        self.assertEqual(Notification.objects.filter(recipient=self.user1).count(), 1)
        notif = Notification.objects.get(recipient=self.user1)
        self.assertEqual(notif.actor, self.user2)
        self.assertEqual(notif.actors.count(), 1)

        # Charlie also likes Alice's entry -> grouped into same notification
        handle_like_toggled(self.public_entry, self.user3, liked=True)
        self.assertEqual(Notification.objects.filter(recipient=self.user1).count(), 1)
        notif.refresh_from_db()
        self.assertEqual(notif.actor, self.user3)
        self.assertEqual(notif.actors.count(), 2)

        title, message = notif.title_and_message
        self.assertIn("charlie, bob", message)

        # Charlie unlikes
        handle_like_toggled(self.public_entry, self.user3, liked=False)
        notif.refresh_from_db()
        self.assertEqual(notif.actor, self.user2)
        self.assertEqual(notif.actors.count(), 1)

        # Bob unlikes -> notification deleted
        handle_like_toggled(self.public_entry, self.user2, liked=False)
        self.assertEqual(Notification.objects.filter(recipient=self.user1).count(), 0)

    def test_parse_mentions(self):
        text = "Hello @bob and @charlie, look at @invaliduser!"
        users = parse_mentions(text)
        self.assertEqual(len(users), 2)
        usernames = {u.username for u in users}
        self.assertIn("bob", usernames)
        self.assertIn("charlie", usernames)

    def test_comment_workflow_with_mentions_and_participants(self):
        """Posting a comment notifies owner, mentioned users, and subscribers."""
        comment = ColonyJournalComment.objects.create(
            entry=self.public_entry,
            user=self.user2,
            comment="Great colony! Hey @charlie what do you think?",
        )
        handle_comment_created(comment)

        # Alice (owner) got ENTRY_COMMENTED
        alice_notif = Notification.objects.filter(
            recipient=self.user1, kind=NotificationKind.ENTRY_COMMENTED
        ).first()
        self.assertIsNotNone(alice_notif)
        self.assertEqual(alice_notif.actor, self.user2)

        # Charlie got MENTIONED
        charlie_notif = Notification.objects.filter(
            recipient=self.user3, kind=NotificationKind.MENTIONED
        ).first()
        self.assertIsNotNone(charlie_notif)
        self.assertEqual(charlie_notif.actor, self.user2)

        # Bob should be subscribed automatically
        self.assertTrue(
            EntrySubscription.objects.filter(
                user=self.user2, entry=self.public_entry
            ).exists()
        )

        # Charlie now replies
        reply = ColonyJournalComment.objects.create(
            entry=self.public_entry,
            user=self.user3,
            comment="I agree, awesome setup!",
        )
        handle_comment_created(reply)

        # Bob should receive THREAD_REPLY
        bob_notif = Notification.objects.filter(
            recipient=self.user2, kind=NotificationKind.THREAD_REPLY
        ).first()
        self.assertIsNotNone(bob_notif)
        self.assertEqual(bob_notif.actor, self.user3)

    def test_muted_thread_suppresses_thread_reply(self):
        """Muting a thread prevents receiving THREAD_REPLY."""
        EntrySubscription.objects.create(
            user=self.user2, entry=self.public_entry, muted=True
        )

        reply = ColonyJournalComment.objects.create(
            entry=self.public_entry,
            user=self.user3,
            comment="Another reply!",
        )
        handle_comment_created(reply)

        bob_reply = Notification.objects.filter(
            recipient=self.user2, kind=NotificationKind.THREAD_REPLY
        ).first()
        self.assertIsNone(bob_reply)

    def test_moderation_notifications(self):
        """Comment removal and force private generate notifications."""
        comment = ColonyJournalComment.objects.create(
            entry=self.public_entry,
            user=self.user2,
            comment="Spam message",
        )
        handle_comment_removed(comment, staff_user=self.staff_user, reason="Spam link")
        mod_notif = Notification.objects.filter(
            recipient=self.user2, kind=NotificationKind.COMMENT_REMOVED
        ).first()
        self.assertIsNotNone(mod_notif)
        self.assertIn("Spam link", mod_notif.extra_data.get("reason", ""))

        handle_colony_forced_private(self.public_colony, staff_user=self.staff_user)
        colony_notif = Notification.objects.filter(
            recipient=self.user1, kind=NotificationKind.COLONY_FORCED_PRIVATE
        ).first()
        self.assertIsNotNone(colony_notif)


class NotificationViewsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="dan", password="password123")
        self.actor = User.objects.create_user(username="elena", password="password123")

        self.genus = Genus.objects.create(name="Myrmica")
        self.species = AntSpecies.objects.create(
            name="Myrmica rubra",
            genus=self.genus,
        )

        self.colony = Colony.objects.create(
            user=self.user,
            species=self.species,
            name="Dan's Ruby Ants",
            is_public=True,
        )

        self.entry = ColonyJournalEntry.objects.create(
            colony=self.colony,
            date="2026-04-10",
            note="First pupae observed!",
        )

        self.client.login(username="dan", password="password123")

    def test_notification_badge_endpoint(self):
        url = reverse("notifications:badge")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'class="notification-badge')
        self.assertIn("d-none", resp.content.decode())

        # Create unread notification
        notify(
            recipient=self.user,
            kind=NotificationKind.ENTRY_LIKED,
            actor=self.actor,
            entry=self.entry,
        )

        resp2 = self.client.get(url)
        self.assertEqual(resp2.status_code, 200)
        self.assertContains(resp2, "1")
        self.assertEqual(
            resp2.headers.get("HX-Trigger"), '{"notificationCountUpdated": 1}'
        )

    def test_notification_dropdown_endpoint(self):
        url = reverse("notifications:dropdown")
        notify(
            recipient=self.user,
            kind=NotificationKind.ENTRY_COMMENTED,
            actor=self.actor,
            entry=self.entry,
        )

        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "elena commented on your journal entry")

    def test_notification_list_page(self):
        url = reverse("notifications:list")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Notifications")
        self.assertContains(resp, "All")

    def test_notification_open_redirect(self):
        notif = notify(
            recipient=self.user,
            kind=NotificationKind.ENTRY_LIKED,
            actor=self.actor,
            entry=self.entry,
        )
        url = reverse("notifications:open", args=[notif.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 302)
        notif.refresh_from_db()
        self.assertTrue(notif.is_read)

    def test_notification_toggle_read(self):
        notif = notify(
            recipient=self.user,
            kind=NotificationKind.ENTRY_LIKED,
            actor=self.actor,
            entry=self.entry,
        )
        self.assertFalse(notif.is_read)

        url = reverse("notifications:toggle_read", args=[notif.pk])
        resp = self.client.post(url, {"action": "read"}, HTTP_HX_REQUEST="true")
        self.assertEqual(resp.status_code, 200)
        notif.refresh_from_db()
        self.assertTrue(notif.is_read)

    def test_notification_mark_all_read(self):
        notify(
            recipient=self.user,
            kind=NotificationKind.ENTRY_LIKED,
            actor=self.actor,
            entry=self.entry,
        )
        notify(
            recipient=self.user,
            kind=NotificationKind.ENTRY_COMMENTED,
            actor=self.actor,
            entry=self.entry,
        )
        self.assertEqual(
            Notification.objects.filter(
                recipient=self.user, read_at__isnull=True
            ).count(),
            2,
        )

        url = reverse("notifications:mark_all_read")
        resp = self.client.post(url, HTTP_HX_REQUEST="true")
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            Notification.objects.filter(
                recipient=self.user, read_at__isnull=True
            ).count(),
            0,
        )

    def test_notification_settings_toggle(self):
        url = reverse("notifications:settings")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Notification Preferences")

        # Toggle in-app for likes to off
        post_resp = self.client.post(
            url,
            {
                "kind": NotificationKind.ENTRY_LIKED,
                "channel": "in_app",
                "enabled": "false",
            },
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(post_resp.status_code, 200)
        pref = NotificationPreference.objects.get(
            user=self.user, kind=NotificationKind.ENTRY_LIKED
        )
        self.assertFalse(pref.in_app)
