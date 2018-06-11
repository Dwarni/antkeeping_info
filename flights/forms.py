"""Forms module for flights app"""
import geocoder
from dal import autocomplete

from django import forms
from django.conf import settings
from django.forms import IntegerField, ChoiceField
from django.forms.widgets import DateInput, TimeInput
from django.utils.translation import ugettext as _

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Field, ButtonHolder, \
    Submit, HTML, Button
from crispy_forms.bootstrap import AppendedText, FormActions

from snowpenguin.django.recaptcha2.fields import ReCaptchaField
from snowpenguin.django.recaptcha2.widgets import ReCaptchaWidget

from ants.models import Species, AntSpecies, AntRegion
from flights.models import Flight, Temperature, Velocity

class Html5DateInput(DateInput):
    """Custom field which automatically activates html5 date input type."""
    input_type = 'date'


class Html5TimeInput(TimeInput):
    """Custom field which automatically activates html5 time input type."""
    input_type = 'time'

class FlightForm(forms.ModelForm):
    """Form class for adding end updating nuptial flights."""

    # general
    test_data = forms.BooleanField(
        required=False
    )
    species = forms.CharField(
        max_length=40,
        validators=Species.name_validators
    )

    # weather
    temperature = IntegerField(required=False)
    temperature_unit = ChoiceField(choices=Temperature.UNIT_CHOICES)
    wind_speed = IntegerField(min_value=0, required=False)
    wind_speed_unit = ChoiceField(choices=Velocity.UNIT_CHOICES, required=False)

    captcha = ReCaptchaField(widget=ReCaptchaWidget, label='')

    helper = FormHelper()

    def __init__(self, *args, **kwargs):
        iframe = kwargs.pop('iframe', None)
        super().__init__(*args, **kwargs)
        self.helper.form_class = 'form-horizontal'
        self.helper.form_id = 'flightForm'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col'
        self.helper.html5_required = True

        cancel_href = '../'
        if iframe:
            cancel_href = cancel_href + '?iframe=true'

        self.helper.layout = Layout(
            Fieldset(_('What?'),
                'species',
                'species_note',
                'spotting_type',
                active=True
            ),
            Fieldset(_('When?'),
                'date',
                'start_time',
                'end_time',
            ),
            Fieldset(_('Where?'),
                'address',
                HTML('<div id="map"></div>'),
                'habitat'
            ),
            Fieldset(_('Weather'),
                'temperature',
                'temperature_unit',
                AppendedText('humidity', '%'),
                'wind_speed',
                'wind_speed_unit',
                'rain',
                'sky_condition'
            ),
            Fieldset(_('Addition information'),
                'comment',
                'link',
                'project',
                'external_user'
            ),
            'captcha',
            ButtonHolder(
                Submit('submit', 'Submit'),
                Submit('add_another_species', 'Submit and add another species'),
                Submit('add_another_flight', 'Submit and add another flight'),
                HTML('<a href="{}" class="btn btn-secondary active" role="button" aria-pressed="true">Cancel</a>'.format(cancel_href)),
            )
        )

        self.country = None
        self.state_short = None
        self.state_long = None
        self.county = None
        self.city_short = None
        self.city_long = None

        self.latitude = None
        self.longitude = None

    def clean(self):
        cleaned_data = super().clean()
        address = cleaned_data.get('address')

        position = geocoder.google(address, key=settings.GOOGLE_API_KEY_SERVER)

        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')

        if start_time is not None and end_time is None:
            self.add_error('end_time', _('Please provide an end time too.'))

        if start_time is None and end_time is not None:
            self.add_error('start_time', _('Please provide a start time too.'))

        if start_time is not None and end_time is not None:
            if start_time > end_time:
                self.add_error('start_time', _('Start time has to be before end time'))
                self.add_error('end_time', _('End time has to be after start time'))

        # Check if api returned a valid result
        if position.status != 'OK':
            self.add_error('address', _('Did not receive a valid result from geocoding API'))
        # Check if at least a city was found
        # elif position.city is None:
        #     self.add_error('address', _("""No city could be found. The address has to
        #         contain at least a city."""))
        else:
            cleaned_data['address'] = position.address
            self.latitude = position.lat
            self.longitude = position.lng
            self.country = AntRegion.objects.get(code=position.country.lower())
            self.state_short = position.state
            self.state_long = position.state_long
            self.county = position.county
            self.city_short = position.city
            self.city_long = position.city_long

        return cleaned_data

    def create_flight(self, user):
        """
            The method will create a Flight model object and add it
            to the database.
        """
        new_flight = Flight()

        return self.safe_flight(new_flight, user)

    def safe_flight(self, flight, user):
        """
            The method will fill and save the passed flight object.
        """

        # general
        species_name = self.cleaned_data.get('species')
        species_note = self.cleaned_data.get('species_note')
        spotting_type = self.cleaned_data.get('spotting_type')
        date = self.cleaned_data.get('date')
        start_time = self.cleaned_data.get('start_time')
        end_time = self.cleaned_data.get('end_time')

        # location
        address = self.cleaned_data.get('address')
        habitat = self.cleaned_data.get('habitat')

        # weather
        temperature = self.cleaned_data.get('temperature')
        temperature_unit = self.cleaned_data.get('temperature_unit')
        humidity = self.cleaned_data.get('humidity')
        wind_speed = self.cleaned_data.get('wind_speed')
        wind_speed_unit = self.cleaned_data.get('wind_speed_unit')
        rain = self.cleaned_data.get('rain')
        sky_condition = self.cleaned_data.get('sky_condition')

        # additional information
        comment = self.cleaned_data.get('comment')
        link = self.cleaned_data.get('link')
        project = self.cleaned_data.get('project')
        external_user = self.cleaned_data.get('external_user')


        # general
        flight.ant_species = AntSpecies.objects.get_or_create_with_name(species_name)
        flight.species_note = species_note
        flight.spotting_type = spotting_type
        flight.date = date
        flight.start_time = start_time
        flight.end_time = end_time

        # location
        flight.address = address
        flight.country = self.country
        flight.state_short = self.state_short
        flight.state_long = self.state_long
        flight.county = self.county
        flight.city_short = self.city_short
        flight.city_long = self.city_long

        flight.latitude = self.latitude
        flight.longitude = self.longitude

        flight.reviewed = user.is_authenticated and user.is_staff

        if user.is_authenticated:
            flight.user = user

        # weather
        if temperature:
            if flight.temperature:
                flight.temperature.value = temperature
                flight.temperature.unit = temperature_unit
                flight.temperature.full_clean()
                flight.temperature.save()
            else:
                new_temperature = Temperature.objects.create(
                    value=temperature, unit=temperature_unit)
                flight.temperature = new_temperature
        flight.humidity = humidity
        if wind_speed:
            if flight.wind_speed:
                flight.wind_speed.vlaue = wind_speed
                flight.wind_speed.unit = wind_speed_unit
                flight.wind_speed.full_clean()
                flight.wind_speed.save()
            else:
                new_wind_speed = Velocity.objects.create(value=wind_speed, unit=wind_speed_unit)
                flight.wind_speed = new_wind_speed

        flight.rain = rain
        flight.sky_condition = sky_condition

        # additional information
        flight.comment = comment
        flight.link = link
        flight.project = project
        flight.external_user = external_user

        flight.full_clean()
        flight.save()
        # tags have to be added after safe
        flight.habitat.add(*habitat)

        return flight

    class Meta:
        model = Flight
        exclude = ['ant_species', 'latitude', 'longitude', 'country',
                   'state_short', 'state_long', 'county', 'city_short',
                   'city_long', 'reviewed', 'temperature', 'wind_speed']
        widgets = {
            'date': Html5DateInput,
            'start_time': Html5TimeInput,
            'end_time': Html5TimeInput,
            'habitat': autocomplete.TaggitSelect2(
                url='flight_habitat_tags_autocomplete'
            )
        }

        labels = {
            'habitat': _('Habitat'),
            'weather_comment': _('Comment')
        }

class FlightStaffForm(FlightForm):
    """Flight form for staff members which does not show the captcha field."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.pop('captcha')
        self.helper.layout.fields.remove('captcha')
