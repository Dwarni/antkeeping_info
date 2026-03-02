from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Field, Layout, Submit
from django import forms
from django.urls import reverse_lazy
from django.utils.safestring import mark_safe


class ContactForm(forms.Form):
    """Contact form with honeypot spam protection and GDPR consent checkbox."""

    name = forms.CharField(max_length=150, label="Your name")
    email = forms.EmailField(label="Your email address")
    subject = forms.CharField(max_length=200, label="Subject")
    message = forms.CharField(widget=forms.Textarea, label="Message")
    # Honeypot: invisible to real users, filled by bots that parse the DOM
    website = forms.CharField(required=False, label="Website")
    send_copy = forms.BooleanField(required=False, label="Send me a copy of this message")
    gdpr_consent = forms.BooleanField(required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        privacy_url = reverse_lazy("privacy")
        self.fields["gdpr_consent"].label = mark_safe(
            f'I have read and agree to the <a href="{privacy_url}">Privacy Policy</a>.'
        )
        self.helper = FormHelper()
        self.helper.layout = Layout(
            "name",
            "email",
            "subject",
            "message",
            Div(
                Field("website", tabindex="-1", autocomplete="off"),
                css_class="visually-hidden",
                aria_hidden="true",
            ),
            "send_copy",
            "gdpr_consent",
            Submit("submit", "Send Message"),
        )
