import time
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail, signing
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from contact.forms import ContactForm
from contact.views import MAX_SUBMISSIONS_PER_HOUR


@override_settings(
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
)
class ContactViewTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = Client()
        self.url = reverse("contact")

    def _get_valid_token(self, age_seconds=10):
        """Generate a token that simulates being created `age_seconds` ago."""
        past_time = time.time() - age_seconds
        with patch("time.time", return_value=past_time):
            return signing.dumps("contact_form")

    def test_contact_get(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "contact/contact.html")
        self.assertIsInstance(response.context["form"], ContactForm)
        self.assertIn("form_token", response.context["form"].initial)
        self.assertContains(response, "Get in Touch")
        self.assertContains(response, "Discord Community")
        self.assertContains(response, "admin@antkeeping.info")

    def test_authenticated_user_prefill(self):
        user = User.objects.create_user(
            username="testkeeper",
            email="keeper@example.com",
            first_name="Jane",
            last_name="Doe",
        )
        self.client.force_login(user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["form"].initial["name"], "Jane Doe")
        self.assertEqual(response.context["form"].initial["email"], "keeper@example.com")
        self.assertContains(response, "testkeeper")

    def test_valid_submission_sends_email(self):
        token = self._get_valid_token(age_seconds=10)
        data = {
            "name": "Jane Antkeeper",
            "email": "jane@example.com",
            "subject": "Question about Camponotus",
            "message": "Hello, I have a question regarding Camponotus ligniperda care.",
            "form_token": token,
            "gdpr_consent": "on",
        }
        response = self.client.post(self.url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)

        sent = mail.outbox[0]
        self.assertEqual(sent.subject, "[Contact] Question about Camponotus")
        self.assertIn("Jane Antkeeper", sent.body)
        self.assertIn("Camponotus ligniperda care", sent.body)
        self.assertEqual(sent.to, [settings.CONTACT_RECIPIENT_EMAIL])
        self.assertContains(response, "Your message has been sent")

    def test_valid_submission_with_copy(self):
        token = self._get_valid_token(age_seconds=10)
        data = {
            "name": "Jane Antkeeper",
            "email": "jane@example.com",
            "subject": "Question about Camponotus",
            "message": "Hello, send me a copy please.",
            "form_token": token,
            "send_copy": "on",
            "gdpr_consent": "on",
        }
        response = self.client.post(self.url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 2)
        # Second email is the copy sent to the user
        copy = mail.outbox[1]
        self.assertEqual(copy.to, ["jane@example.com"])
        self.assertEqual(copy.subject, "[Copy] Question about Camponotus")

    def test_honeypot_discarded(self):
        token = self._get_valid_token(age_seconds=10)
        data = {
            "name": "Spam Bot",
            "email": "bot@spam.com",
            "subject": "Buy cheap stuff",
            "message": "Spam message content",
            "phone": "+123456789",  # Honeypot filled!
            "form_token": token,
            "gdpr_consent": "on",
        }
        response = self.client.post(self.url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        # Email must NOT be sent
        self.assertEqual(len(mail.outbox), 0)
        # Fake success message is shown to bot
        self.assertContains(response, "Your message has been sent")

    def test_too_fast_bot_discarded(self):
        # Token generated 0.5s ago (< MIN_SUBMIT_SECONDS of 3)
        token = self._get_valid_token(age_seconds=0.5)
        data = {
            "name": "Fast Bot",
            "email": "bot@fast.com",
            "subject": "Fast submission",
            "message": "Instant message",
            "form_token": token,
            "gdpr_consent": "on",
        }
        response = self.client.post(self.url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)
        self.assertContains(response, "Your message has been sent")

    def test_invalid_or_expired_token(self):
        data = {
            "name": "User",
            "email": "user@example.com",
            "subject": "Test",
            "message": "Test message",
            "form_token": "tampered-bad-token",
            "gdpr_consent": "on",
        }
        response = self.client.post(self.url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)
        self.assertContains(response, "Your session has expired")

    def test_validation_errors(self):
        data = {
            "name": "",
            "email": "not-an-email",
            "subject": "",
            "message": "",
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)
        form = response.context["form"]
        self.assertIn("name", form.errors)
        self.assertIn("email", form.errors)
        self.assertIn("subject", form.errors)
        self.assertIn("message", form.errors)
        self.assertIn("gdpr_consent", form.errors)

    def test_rate_limiting(self):
        token = self._get_valid_token(age_seconds=10)
        data = {
            "name": "Active User",
            "email": "active@example.com",
            "subject": "Hello",
            "message": "Message body",
            "form_token": token,
            "gdpr_consent": "on",
        }

        # Send MAX_SUBMISSIONS_PER_HOUR valid messages
        for i in range(MAX_SUBMISSIONS_PER_HOUR):
            token = self._get_valid_token(age_seconds=10)
            data["form_token"] = token
            resp = self.client.post(self.url, data)
            self.assertEqual(resp.status_code, 302)

        self.assertEqual(len(mail.outbox), MAX_SUBMISSIONS_PER_HOUR)

        # The next attempt should trigger rate limiting
        token = self._get_valid_token(age_seconds=10)
        data["form_token"] = token
        resp = self.client.post(self.url, data)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(mail.outbox), MAX_SUBMISSIONS_PER_HOUR)  # No new email
        messages = list(resp.context["messages"])
        self.assertTrue(any("too many messages" in str(m) for m in messages))
