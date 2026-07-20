"""
Forms module for users app.
"""

import logging

import requests
from allauth.account.forms import SignupForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import ButtonHolder, Fieldset, Layout, Submit
from disposable_email_domains import blocklist
from django.conf import settings
from django.contrib.auth import forms as auth_forms
from django.contrib.auth import models as auth_models
from django.core.exceptions import ValidationError
from django.forms import ModelForm

logger = logging.getLogger(__name__)

TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


class SaveLayout(Layout):
    """Layout class with a 'Save'-Button at the end."""

    def __init__(self, *fields):
        super().__init__(*fields)
        self.fields.append(ButtonHolder(Submit("Save", "Save")))


class CustomAuthentificationForm(auth_forms.AuthenticationForm):
    """Log in form."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.layout_fieldset = Fieldset("Log In", "username", "password")
        self.helper.layout = Layout(
            self.layout_fieldset, ButtonHolder(Submit("Log In", "Log In"))
        )


class ProfileForm(ModelForm):
    """User profile form."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = SaveLayout(
            Fieldset("Edit Profile", "first_name", "last_name")
        )

    class Meta:
        model = auth_models.User
        fields = ["first_name", "last_name"]


class RegistrationForm(auth_forms.UserCreationForm):
    """User registration form."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = SaveLayout(
            Fieldset("User Registration", "username", "password1", "password2")
        )


class CustomSignupForm(SignupForm):
    """Allauth signup form with a Cloudflare Turnstile bot check.

    The honeypot field is provided by allauth itself, via
    ACCOUNT_SIGNUP_FORM_HONEYPOT_FIELD.
    """

    def clean_email(self):
        email = super().clean_email()
        domain = email.rsplit("@", 1)[-1].lower()
        if domain in blocklist:
            raise ValidationError("Please use a permanent email address.")
        return email

    def clean(self):
        cleaned_data = super().clean()

        # self.request is not set by allauth's SignupView, so the token is
        # read straight from the bound POST data instead.
        token = self.data.get("cf-turnstile-response", "")
        if not self._verify_turnstile(token):
            logger.info("Signup blocked: Turnstile verification failed")
            raise ValidationError("Please complete the human verification challenge.")

        return cleaned_data

    def _verify_turnstile(self, token: str) -> bool:
        if not token:
            return False
        try:
            response = requests.post(
                TURNSTILE_VERIFY_URL,
                data={"secret": settings.TURNSTILE_SECRET_KEY, "response": token},
                timeout=5,
            )
            return response.json().get("success", False)
        except requests.RequestException:
            logger.exception("Turnstile verification request failed")
            return False
