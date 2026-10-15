from django.test import Client, TestCase
from django.urls import reverse


class LegalAndPrivacyPagesTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_legal_notice_page_renders_successfully(self):
        url = reverse("legal")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "legal_notice.html")
        self.assertContains(response, "Legal Notice")
        self.assertContains(response, "§ 5 DDG")
        self.assertContains(response, "Andreas Weggel")
        self.assertContains(response, "Dahlienweg 2")
        self.assertContains(response, "admin@antkeeping.info")
        self.assertContains(response, "CC BY 4.0")
        self.assertContains(response, "Solar Icons")
        self.assertContains(response, "framework7io")

    def test_privacy_policy_page_renders_successfully(self):
        url = reverse("privacy")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "privacy_policy.html")
        self.assertContains(response, "Privacy Policy")
        self.assertContains(response, "GDPR")
        self.assertContains(response, "Webserver Log Files")
        self.assertContains(response, "Cookies & Local Storage")
        self.assertContains(response, "sessionid")
        self.assertContains(response, "csrftoken")
        self.assertContains(response, "Cloudflare")
        self.assertContains(response, "admin@antkeeping.info")
