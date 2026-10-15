from crispy_forms.helper import FormHelper
from crispy_forms.layout import Column, Div, Field, Layout, Row, Submit
from django import forms
from django.urls import reverse_lazy
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _


class ContactForm(forms.Form):
    """Contact form with multi-layer spam protection and GDPR consent checkbox."""

    name = forms.CharField(
        max_length=150,
        label=_("Your name"),
        widget=forms.TextInput(
            attrs={
                "autocomplete": "name",
                "placeholder": _("e.g. Jane Doe"),
            }
        ),
        error_messages={"required": _("Please enter your name.")},
    )
    email = forms.EmailField(
        label=_("Your email address"),
        widget=forms.EmailInput(
            attrs={
                "autocomplete": "email",
                "placeholder": _("name@example.com"),
            }
        ),
        error_messages={
            "required": _("Please enter your email address."),
            "invalid": _("Please enter a valid email address."),
        },
    )
    subject = forms.CharField(
        max_length=200,
        label=_("Subject"),
        widget=forms.TextInput(
            attrs={
                "placeholder": _("What is your inquiry about?"),
            }
        ),
        error_messages={"required": _("Please provide a subject.")},
    )
    message = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "rows": 6,
                "placeholder": _("Write your message here..."),
                "maxlength": "5000",
            }
        ),
        label=_("Message"),
        error_messages={"required": _("Please enter a message.")},
    )
    # Honeypot fields: invisible to real users, filled by bots that parse the DOM.
    # Named after plausible form fields to avoid triggering bot honeypot detection.
    phone = forms.CharField(
        required=False,
        label=_("Phone"),
        widget=forms.TextInput(
            attrs={"tabindex": "-1", "autocomplete": "off"}
        ),
    )
    address = forms.CharField(
        required=False,
        label=_("Address"),
        widget=forms.TextInput(
            attrs={"tabindex": "-1", "autocomplete": "off"}
        ),
    )
    # Signed timestamp token for time-gate check (injected by the view via get_initial).
    form_token = forms.CharField(required=False, widget=forms.HiddenInput)
    send_copy = forms.BooleanField(
        required=False,
        label=_("Send me a copy of this message"),
    )
    gdpr_consent = forms.BooleanField(
        required=True,
        error_messages={
            "required": _("You must agree to the Privacy Policy to send a message.")
        },
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        privacy_url = reverse_lazy("privacy")
        self.fields["gdpr_consent"].label = mark_safe(
            f'{_("I have read and agree to the")} '
            f'<a href="{privacy_url}" target="_blank" rel="noopener">'
            f'{_("Privacy Policy")}</a> <span class="text-danger">*</span>'
        )
        self.helper = FormHelper()
        self.helper.form_id = "contactForm"
        self.helper.form_method = "post"
        self.helper.form_class = "needs-validation"
        self.helper.attrs = {"novalidate": ""}
        self.helper.layout = Layout(
            Row(
                Column(Field("name", wrapper_class="mb-3"), css_class="col-md-6"),
                Column(Field("email", wrapper_class="mb-3"), css_class="col-md-6"),
                css_class="g-3 mb-1",
            ),
            Field("subject", wrapper_class="mb-3"),
            Field("message", wrapper_class="mb-3"),
            Div(
                Field("phone"),
                Field("address"),
                css_class="d-none",
                aria_hidden="true",
            ),
            Field("form_token"),
            Field("send_copy", wrapper_class="form-check mb-2"),
            Field("gdpr_consent", wrapper_class="form-check mb-4"),
            Div(
                Submit(
                    "submit",
                    _("Send Message"),
                    css_class="btn btn-primary px-4 py-2 fw-semibold d-inline-flex align-items-center gap-2",
                    id="contactSubmitBtn",
                ),
                css_class="d-grid d-sm-flex justify-content-sm-start",
            ),
        )
