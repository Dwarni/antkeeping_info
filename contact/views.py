import logging

from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.urls import reverse_lazy
from django.views.generic import FormView

from .forms import ContactForm

logger = logging.getLogger(__name__)


class ContactView(FormView):
    template_name = "contact/contact.html"
    form_class = ContactForm
    success_url = reverse_lazy("contact")

    def form_valid(self, form):
        # Honeypot check: if 'website' is filled, silently discard (don't inform bots)
        if form.cleaned_data.get("website"):
            messages.success(
                self.request,
                "Your message has been sent. Thank you for contacting us!",
            )
            return super().form_valid(form)

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
