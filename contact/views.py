import logging

from django.conf import settings
from django.contrib import messages
from django.core import signing
from django.core.cache import cache
from django.core.mail import send_mail
from django.urls import reverse_lazy
from django.views.generic import FormView

from .forms import ContactForm

logger = logging.getLogger(__name__)

MIN_SUBMIT_SECONDS = 3        # Reject submissions faster than this (bots submit instantly)
MAX_SUBMISSIONS_PER_HOUR = 3
RATE_LIMIT_TIMEOUT = 3600     # Cache key TTL in seconds


class ContactView(FormView):
    template_name = "contact/contact.html"
    form_class = ContactForm
    success_url = reverse_lazy("contact")

    def get_initial(self):
        """Inject a signed timestamp token so form_valid() can verify elapsed time."""
        initial = super().get_initial()
        initial["form_token"] = signing.dumps("contact_form")
        return initial

    def _is_rate_limited(self, request) -> bool:
        """
        Return True if this IP has exceeded the hourly submission limit.
        Increments the counter on each call, so only call once per valid submission.
        """
        ip = request.META.get("REMOTE_ADDR", "unknown")
        cache_key = f"contact_form_submissions_{ip}"
        count = cache.get(cache_key, 0)
        if count >= MAX_SUBMISSIONS_PER_HOUR:
            return True
        cache.set(cache_key, count + 1, timeout=RATE_LIMIT_TIMEOUT)
        return False

    def form_valid(self, form):
        ip = self.request.META.get("REMOTE_ADDR")

        # --- Layer 2: Honeypot check ---
        # Bots that fill hidden fields are silently discarded (fake success response).
        if form.cleaned_data.get("phone") or form.cleaned_data.get("address"):
            logger.info("Spam discarded: honeypot filled (IP: %s)", ip)
            messages.success(
                self.request,
                "Your message has been sent. Thank you for contacting us!",
            )
            return super().form_valid(form)

        # --- Layer 1: Signed timestamp token ---
        token = form.cleaned_data.get("form_token", "")
        try:
            # First check: is the token valid at all and not over an hour old?
            signing.loads(token, max_age=3600)
        except signing.SignatureExpired:
            # Legitimate user on a very old cached page — re-render with a fresh token.
            messages.warning(self.request, "Your session has expired. Please try again.")
            form.initial["form_token"] = signing.dumps("contact_form")
            return self.form_invalid(form)
        except signing.BadSignature:
            # Missing, empty, or tampered token — treat as bot.
            logger.info("Spam discarded: bad form_token (IP: %s)", ip)
            messages.success(
                self.request,
                "Your message has been sent. Thank you for contacting us!",
            )
            return super().form_valid(form)

        try:
            # Second check: was the form submitted too quickly?
            # If loads() succeeds, the token is under MIN_SUBMIT_SECONDS old → bot.
            signing.loads(token, max_age=MIN_SUBMIT_SECONDS)
            logger.info("Spam discarded: submitted too fast (IP: %s)", ip)
            messages.success(
                self.request,
                "Your message has been sent. Thank you for contacting us!",
            )
            return super().form_valid(form)
        except signing.SignatureExpired:
            pass  # Token is old enough — human-plausible timing, continue.

        # --- Layer 3: IP-based rate limiting ---
        if self._is_rate_limited(self.request):
            logger.warning("Rate limit exceeded (IP: %s)", ip)
            messages.error(
                self.request,
                "You have sent too many messages recently. Please wait before trying again.",
            )
            return self.form_invalid(form)

        # --- All checks passed: send the email ---
        name = form.cleaned_data["name"]
        email = form.cleaned_data["email"]
        subject = form.cleaned_data["subject"]
        message_body = form.cleaned_data["message"]
        send_copy = form.cleaned_data["send_copy"]

        email_body = (
            f"Contact form submission from {name} <{email}>\n"
            f"{'=' * 60}\n\n"
            f"{message_body}\n\n"
            f"{'=' * 60}\n"
            f"Reply to: {email}"
        )

        try:
            send_mail(
                subject=f"[Contact] {subject}",
                message=email_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.CONTACT_RECIPIENT_EMAIL],
                fail_silently=False,
            )
        except Exception:
            logger.exception("Failed to send contact form email")
            messages.error(
                self.request,
                "Sorry, there was an error sending your message. Please try again later.",
            )
            return self.form_invalid(form)

        if send_copy:
            copy_body = (
                f"This is a copy of your message sent via antkeeping.info.\n\n"
                f"{'=' * 60}\n\n"
                f"{message_body}\n\n"
                f"{'=' * 60}\n"
            )
            try:
                send_mail(
                    subject=f"[Copy] {subject}",
                    message=copy_body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=False,
                )
            except Exception:
                logger.exception("Failed to send copy email to %s", email)

        messages.success(
            self.request,
            "Your message has been sent. Thank you for contacting us!",
        )
        return super().form_valid(form)
