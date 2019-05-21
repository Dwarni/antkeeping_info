"""Forms module for staff app."""
from django import forms

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit

from ants.models import AntRegion


class AddAntspeciesToRegionForm(forms.Form):
    """Form for adding a list of species to a region."""
    region = forms.ModelChoiceField(queryset=AntRegion.objects.all())
    create_missing_species = forms.BooleanField(required=False, initial=False)
    species = forms.CharField(widget=forms.Textarea)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'region',
            'create_missing_species',
            'species',
            Submit('submit', 'Submit')
        )
