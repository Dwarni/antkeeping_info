"""
Forms module for users app.
"""

import logging

import requests
from allauth.account.forms import SignupForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import ButtonHolder, Fieldset, Layout, Submit
from disposable_email_domains import blocklist
from django import forms
from django.conf import settings
from django.contrib.auth import forms as auth_forms
from django.contrib.auth import models as auth_models
from django.core.exceptions import ValidationError
from django.forms import ModelForm
from django.utils.translation import gettext_lazy as _

from .models import UserProfile

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


class UserProfileSettingsForm(forms.ModelForm):
    """User profile settings form updating User and UserProfile."""

    first_name = forms.CharField(
        label=_("First name"),
        max_length=150,
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": _("First name")}
        ),
    )
    last_name = forms.CharField(
        label=_("Last name"),
        max_length=150,
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": _("Last name")}
        ),
    )
    remove_avatar = forms.BooleanField(
        required=False,
        widget=forms.HiddenInput(),
    )

    class Meta:
        model = UserProfile
        fields = [
            "avatar",
            "bio",
            "location",
            "show_full_name",
            "show_location",
            "show_bio",
        ]
        widgets = {
            "avatar": forms.FileInput(
                attrs={
                    "class": "form-control",
                    "accept": "image/jpeg,image/png,image/webp,image/gif",
                }
            ),
            "bio": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": _(
                        "Share a little about yourself, your colonies, or your experience..."
                    ),
                }
            ),
            "location": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": _("City, Country (optional)"),
                }
            ),
            "show_full_name": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "show_location": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "show_bio": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        if user and user.pk and "instance" not in kwargs:
            kwargs["instance"] = UserProfile.objects.get_or_create(user=user)[0]
        super().__init__(*args, **kwargs)
        if self.user:
            self.fields["first_name"].initial = self.user.first_name
            self.fields["last_name"].initial = self.user.last_name

    def clean_avatar(self):
        avatar = self.cleaned_data.get("avatar")
        if avatar:
            content_type = getattr(avatar, "content_type", "")
            if content_type and not content_type.startswith("image/"):
                raise ValidationError(
                    _("Only image files (JPG, PNG, WebP) are allowed.")
                )
            if hasattr(avatar, "size") and avatar.size > 5 * 1024 * 1024:
                raise ValidationError(_("Avatar image file size cannot exceed 5 MB."))
        return avatar

    def save(self, commit=True):
        profile = super().save(commit=False)
        if self.cleaned_data.get("remove_avatar"):
            if profile.avatar:
                profile.avatar.delete(save=False)
            profile.avatar = None

        if commit:
            profile.save()
            if self.user:
                self.user.first_name = self.cleaned_data.get("first_name", "")
                self.user.last_name = self.cleaned_data.get("last_name", "")
                self.user.save(update_fields=["first_name", "last_name"])
        return profile


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
