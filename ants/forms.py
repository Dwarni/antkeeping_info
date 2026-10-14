from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Column, Div, Field, Layout, Row, Submit
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django import forms
from django.urls import reverse_lazy
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from ants.models import AntSpecies, Colony, ColonyCareEvent, ColonyCensus, ColonyJournalComment, ColonyJournalEntry, FoodItem, Month
from ants.utils.partial_date import PartialDateField


def _label_with_help(label, help_text):
    """A field label with a small "?" icon that opens `help_text` in a popover
    (activated globally by global_static/js/layout.js's activatePopovers()).

    Uses a real <button>, not a <span> -- a label forwards clicks on plain
    descendants to its associated input/checkbox, which would otherwise
    toggle a checkbox just from clicking the help icon.
    """
    return format_html(
        '{} <button type="button" class="btn btn-link btn-sm p-0 border-0 align-baseline" '
        'data-bs-toggle="popover" data-bs-trigger="focus" data-bs-placement="right" '
        'data-bs-content="{}"><i class="bi bi-question-circle"></i></button>',
        label, help_text,
    )


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


class FoodItemCreateForm(forms.ModelForm):
    """Form for logged-in users to suggest a new food item for the catalog."""

    class Meta:
        model = FoodItem
        fields = [
            "name", "category", "description", "image",
            "image_author", "image_license", "image_source_url",
        ]
        widgets = {"category": forms.HiddenInput()}

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("image_license") and not cleaned_data.get("image_author"):
            self.add_error(
                "image_author",
                "Please name the author for attribution when specifying an image license.",
            )
        return cleaned_data


class ColonyForm(forms.ModelForm):
    """Form for creating or editing a colony."""

    # Hidden field — validated server-side; populated via JS from the autocomplete UI
    species = forms.ModelChoiceField(
        queryset=AntSpecies.objects.filter(valid=True).order_by("name"),
        widget=forms.HiddenInput(),
        label="Ant species",
        error_messages={
            "required": "Please select a species from the suggestions.",
            "invalid_choice": "Please select a valid species from the suggestions.",
        },
    )

    status = forms.ChoiceField(
        choices=Colony.STATUS_CHOICES,
        initial=Colony.ACTIVE,
        required=False,
        label=_label_with_help(
            "Status",
            "Current development phase of the colony (e.g. Founding queen in tube, Active, Hibernating).",
        ),
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    # Initial population / Volksstärke (available on colony creation)
    initial_queens = forms.IntegerField(
        required=False,
        min_value=0,
        initial=1,
        label=_label_with_help(
            "Queens (initial count)",
            "Number of queens currently in the colony (default: 1).",
        ),
        widget=forms.NumberInput(attrs={"class": "form-control", "placeholder": "1"}),
    )
    initial_workers = forms.IntegerField(
        required=False,
        min_value=0,
        initial=0,
        label=_label_with_help(
            "Workers (initial count)",
            "Number of workers currently in the colony (0 for a founding queen in a test tube).",
        ),
        widget=forms.NumberInput(attrs={"class": "form-control", "placeholder": "0"}),
    )
    initial_estimated = forms.BooleanField(
        required=False,
        label="Worker / queen count is estimated (approximate)",
    )

    # found_date/purchase_date are handled outside Meta.fields: each maps to
    # *two* model fields (date + precision), which a plain ModelForm mapping
    # can't express. See save() below for how they get written back.
    found_date = PartialDateField(
        label=_label_with_help(
            "Found date",
            "Don't remember the exact day? Just fill in the year, or the year and month.",
        )
    )
    purchase_date = PartialDateField(
        label=_label_with_help(
            "Purchase date",
            "Don't remember the exact day? Just fill in the year, or the year and month.",
        )
    )

    # Colonies (and their found_location) are public by default; these two
    # fields are the inverse of Colony.is_public/share_found_location so the
    # checkboxes read as an opt-OUT ("keep private"), not an opt-in. See
    # save() below for how they get flipped back onto the model fields.
    keep_private = forms.BooleanField(
        required=False,
        label=_label_with_help(
            "Keep this colony private",
            "Colonies are public by default. Check this to hide it from everyone but you.",
        ),
    )
    hide_found_location = forms.BooleanField(
        required=False,
        label=_label_with_help(
            "Hide found location from the public page",
            "Even on a public colony, you can keep just the found location to yourself.",
        ),
    )

    class Meta:
        model = Colony
        fields = [
            "species", "name", "status", "origin_type", "found_location", "purchase_shop",
        ]

    def clean_status(self):
        return self.cleaned_data.get("status") or Colony.ACTIVE

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["name"].label = _label_with_help(
            "Name", "Anything you like — it just needs to be unique among your own colonies."
        )
        self.fields["found_location"].label = _label_with_help(
            "Found location",
            "As precise or vague as you like — a country or region is fine if you'd "
            "rather not share more.",
        )
        self.fields["purchase_shop"].label = _label_with_help(
            "Purchase from", "A shop name, or the username/handle of whoever you got it from."
        )
        is_edit = bool(self.instance.pk)
        if is_edit:
            # Species is immutable after creation: changing it would orphan
            # journal history recorded against the original species.
            self.fields["species"].disabled = True
            self.fields["found_date"].initial = (
                self.instance.found_date, self.instance.found_date_precision
            )
            self.fields["purchase_date"].initial = (
                self.instance.purchase_date, self.instance.purchase_date_precision
            )
            self.fields["keep_private"].initial = not self.instance.is_public
            self.fields["hide_found_location"].initial = not self.instance.share_found_location
        self.helper = FormHelper()
        self.helper.form_tag = False

        if not is_edit:
            basics_div = Div(
                HTML('<h6 class="text-muted mb-3"><i class="bi bi-info-circle me-1"></i>Basics</h6>'),
                "name",
                "status",
                HTML('<hr class="my-3"><h6 class="text-muted mb-2"><i class="bi bi-people-fill me-1"></i>Initial Population / Volksstärke (optional)</h6><p class="small text-muted mb-3">Record your queen & worker counts so your colony dashboard immediately shows its current size.</p>'),
                Row(
                    Column("initial_queens", css_class="col-md-6 mb-2"),
                    Column("initial_workers", css_class="col-md-6 mb-2"),
                ),
                "initial_estimated",
                css_class="border rounded p-3 mb-3",
            )
        else:
            basics_div = Div(
                HTML('<h6 class="text-muted mb-3"><i class="bi bi-info-circle me-1"></i>Basics</h6>'),
                "name",
                "status",
                css_class="border rounded p-3 mb-3",
            )

        # species (HiddenInput) is rendered manually in the template before crispy output
        self.helper.layout = Layout(
            basics_div,
            Div(
                HTML('<h6 class="text-muted mb-3"><i class="bi bi-geo-alt-fill me-1"></i>Where it came from</h6>'),
                "origin_type",
                "found_location",
                "found_date",
                "purchase_date",
                "purchase_shop",
                css_class="border rounded p-3 mb-3",
            ),
            Div(
                HTML('<h6 class="text-muted mb-3"><i class="bi bi-shield-lock-fill me-1"></i>Privacy</h6>'),
                "keep_private",
                "hide_found_location",
                css_class="border rounded p-3 mb-3",
            ),
            Submit("submit", "Save colony"),
        )

    def save(self, commit=True):
        is_new = not self.instance.pk
        instance = super().save(commit=False)
        for field_name, precision_field in [
            ("found_date", "found_date_precision"),
            ("purchase_date", "purchase_date_precision"),
        ]:
            value = self.cleaned_data.get(field_name)
            date_value, precision = value if value else (None, "")
            setattr(instance, field_name, date_value)
            setattr(instance, precision_field, precision)
        instance.is_public = not self.cleaned_data.get("keep_private")
        instance.share_found_location = not self.cleaned_data.get("hide_found_location")
        if commit:
            instance.save()
            if is_new:
                queens = self.cleaned_data.get("initial_queens")
                workers = self.cleaned_data.get("initial_workers")
                estimated = bool(self.cleaned_data.get("initial_estimated"))
                if queens is not None or workers is not None:
                    census_date = instance.found_date or instance.purchase_date or timezone.now().date()
                    ColonyCensus.objects.create(
                        colony=instance,
                        date=census_date,
                        queens=queens,
                        queens_is_estimated=estimated,
                        workers=workers,
                        workers_is_estimated=estimated,
                        note="Initial count upon adding colony",
                    )
        return instance


class ColonyJournalEntryForm(forms.ModelForm):
    """Form for a single colony journal entry. Photos are handled separately
    in the view since an entry can carry several of them."""

    class Meta:
        model = ColonyJournalEntry
        fields = ["date", "event_type", "note"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date", "class": "form-control form-control-sm"}),
            "event_type": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "note": forms.Textarea(attrs={"rows": 3, "class": "form-control form-control-sm"}),
        }


class ColonyCensusForm(forms.ModelForm):
    """Form for recording counts of castes and brood stages."""

    eggs_unit = forms.ChoiceField(
        choices=ColonyCensus.EGG_UNIT_CHOICES,
        required=False,
        initial=ColonyCensus.UNIT_EGGS,
        widget=forms.Select(attrs={"class": "form-select form-select-sm"}),
    )

    def clean_eggs_unit(self):
        return self.cleaned_data.get("eggs_unit") or ColonyCensus.UNIT_EGGS

    class Meta:
        model = ColonyCensus
        fields = [
            "date",
            "queens",
            "queens_is_estimated",
            "workers",
            "workers_is_estimated",
            "eggs",
            "eggs_unit",
            "eggs_is_estimated",
            "larvae",
            "larvae_is_estimated",
            "pupae",
            "pupae_is_estimated",
            "image_file",
            "note",
        ]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date", "class": "form-control form-control-sm"}),
            "queens": forms.NumberInput(attrs={"min": 0, "class": "form-control form-control-sm", "placeholder": "e.g. 1"}),
            "queens_is_estimated": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "workers": forms.NumberInput(attrs={"min": 0, "class": "form-control form-control-sm", "placeholder": "e.g. 25"}),
            "workers_is_estimated": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "eggs": forms.NumberInput(attrs={"min": 0, "class": "form-control form-control-sm", "placeholder": "e.g. 15"}),
            "eggs_unit": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "eggs_is_estimated": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "larvae": forms.NumberInput(attrs={"min": 0, "class": "form-control form-control-sm", "placeholder": "e.g. 10"}),
            "larvae_is_estimated": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "pupae": forms.NumberInput(attrs={"min": 0, "class": "form-control form-control-sm", "placeholder": "e.g. 5"}),
            "pupae_is_estimated": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "image_file": forms.ClearableFileInput(
                attrs={"class": "d-none photo-picker-file-input", "accept": "image/*"}
            ),
            "note": forms.TextInput(attrs={"class": "form-control form-control-sm", "placeholder": "Optional note (e.g. counted via photo)"}),
        }


class ColonyCareEventForm(forms.ModelForm):
    """Form for recording a maintenance or care event."""

    class Meta:
        model = ColonyCareEvent
        fields = ["category", "date", "time", "food_item", "details"]
        widgets = {
            "category": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "date": forms.DateInput(attrs={"type": "date", "class": "form-control form-control-sm"}),
            "time": forms.TimeInput(attrs={"type": "time", "class": "form-control form-control-sm"}),
            "food_item": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "details": forms.TextInput(attrs={"class": "form-control form-control-sm", "placeholder": "e.g. Honey water & small cricket"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["food_item"].queryset = FoodItem.objects.all().order_by("name")
        self.fields["food_item"].required = False


class ColonyJournalCommentForm(forms.ModelForm):
    """Form for posting a comment on a colony journal entry."""

    class Meta:
        model = ColonyJournalComment
        fields = ["comment"]
        widgets = {
            "comment": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Write a comment...",
                    "maxlength": 1000,
                }
            )
        }
