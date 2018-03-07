from django import forms
from regions.models import Country, Region


def create_country_field():
    query_set = Country.objects.filter(ant_list_complete=True)
    field = forms.ModelChoiceField(
        queryset=query_set,
        to_field_name='code'
    )
    return field


def create_region_field(country_code):
    query_set = Region.objects.filter(ant_list_complete=True)
    query_set = query_set.filter(country__code=country_code)
    field = forms.ModelChoiceField(queryset=query_set)
    return field


def create_region_antlist_form(country_id=None, region_id=None):
    form = forms.Form(initial={
        'country': country_id,
        'region': region_id
    })
    form.fields['country'] = create_country_field(country_id)
    if country_id is not None:
        form.fields['region'] = create_region_field(country_id)
    return form


def country_is_valid(country_code):
    result = None
    if country_code is not None:
        result = Country.objects \
            .filter(code=country_code) \
            .filter(ant_list_complete=True) \
            .exists()

    return result


class AntlistForm(forms.Form):
    country = create_country_field()

    def __init__(self, country_code, *args, **kwargs):
        super(AntlistForm, self).__init__(*args, **kwargs)

        if country_is_valid(country_code):
            self.fields['country'].initial = country_code
            self.fields['region'] = create_region_field(country_code)
