from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Field, Layout, Submit
from django import forms
from django.urls import reverse_lazy
from django.utils.safestring import mark_safe

from ants.models import AntSpecies, Month


class NuptialFlightReportForm(forms.Form):
    """Form for users to report nuptial flight month data for an ant species."""

    # Hidden field — validated server-side; populated via JS from the autocomplete UI
    ant_species = forms.ModelChoiceField(
        queryset=AntSpecies.objects.filter(valid=True).order_by("name"),
        widget=forms.HiddenInput(),
        label="Ant species",
        error_messages={
            "required": "Please select a species from the suggestions.",
            "invalid_choice": "Please select a valid species from the suggestions.",
        },
    )
    months = forms.ModelMultipleChoiceField(
        queryset=Month.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        label="Swarming months",
    )
    source = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 4}),
        label="Source / Notes",
        help_text="Where does this data come from, or what is wrong with the existing data?",
    )
    name = forms.CharField(max_length=150, label="Your name")
    email = forms.EmailField(label="Your email address")
    send_copy = forms.BooleanField(required=False, label="Send me a copy of this message")
    # Honeypot: invisible to real users, filled by bots that parse the DOM
    website = forms.CharField(required=False, label="Website")
    gdpr_consent = forms.BooleanField(required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        privacy_url = reverse_lazy("privacy")
        self.fields["gdpr_consent"].label = mark_safe(
            f'I have read and agree to the <a href="{privacy_url}">Privacy Policy</a>.'
        )
        self.helper = FormHelper()
        self.helper.form_tag = False
        # ant_species (HiddenInput) is rendered manually in the template before crispy output
        self.helper.layout = Layout(
            "months",
            "source",
            "name",
            "email",
            Div(
                Field("website", tabindex="-1", autocomplete="off"),
                css_class="visually-hidden",
                aria_hidden="true",
            ),
            "send_copy",
            "gdpr_consent",
            Submit("submit", "Submit Report"),
        )
