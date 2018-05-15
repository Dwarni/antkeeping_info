"""Forms module for flights app"""
from django import forms
from django.conf import settings
from django.forms import IntegerField, ChoiceField
from django.forms.widgets import DateInput, TimeInput
from django.utils.translation import ugettext as _
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Fieldset, ButtonHolder, \
    Submit, HTML, Div
from crispy_forms.bootstrap import AppendedText
from snowpenguin.django.recaptcha2.fields import ReCaptchaField
from snowpenguin.django.recaptcha2.widgets import ReCaptchaWidget
import geocoder
from ants.models import Species, AntSpecies
from flights.models import Flight, Temperature, Velocity


class Html5DateInput(DateInput):
    """Custom field which automatically activates html5 date input type."""
    input_type = 'date'


class Html5TimeInput(TimeInput):
    """Custom field which automatically activates html5 time input type."""
    input_type = 'time'


class FlightForm(forms.Form):
    """Form class for adding end updating nuptial flights."""

    # general
    species = forms.CharField(
        max_length=40,
        validators=Species.name_validators
    )
    SPOTTING_TYPE_CHOICES = (
        ('', ''),
    ) + Flight.SPOTTING_TYPE_CHOICES
    spotting_type = forms.ChoiceField(
        choices=SPOTTING_TYPE_CHOICES
    )
    date = forms.DateField(widget=Html5DateInput())
    time = forms.TimeField(
        widget=Html5TimeInput(),
        required=False
    )
    comment = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 5}),
        max_length=250,
        label='',
        required=False
    )

    # location
    address = forms.CharField(
        max_length=100,
        required=True,
    )

    # weather
    temperature = IntegerField(required=False)
    temperature_unit = ChoiceField(choices=Temperature.UNIT_CHOICES)
    humidity = forms.IntegerField(min_value=0, required=False)
    wind_speed = IntegerField(min_value=0, required=False)
    wind_speed_unit = ChoiceField(choices=Velocity.UNIT_CHOICES, required=False)
    captcha = ReCaptchaField(widget=ReCaptchaWidget, label='')

    helper = FormHelper()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper.form_class = 'form-horizontal'
        self.helper.form_id = 'flightForm'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col'
        self.helper.html5_required = True
        self.helper.layout = Layout(
            Fieldset(
                'General',
                'species',
                'spotting_type',
                'date',
                'time',
            ),
            Fieldset(
                'Location',
                'address',
                HTML('<div id="map"></div>')
            ),
            Fieldset(
                _('Weather'),
                'temperature',
                'temperature_unit',
                AppendedText('humidity', '%'),
                'wind_speed',
                'wind_speed_unit'
            ),
            Fieldset(
                'Comment',
                'comment',
            ),
            'captcha',
            ButtonHolder(
                Submit('submit', 'Submit')
            )
        )

        self.country_code = None
        self.state_code = None
        self.state_name = None
        self.latitude = None
        self.longitude = None

    def clean(self):
        cleaned_data = super().clean()
        address = cleaned_data.get('address')

        position = geocoder.google(address, key=settings.GOOGLE_API_KEY_SERVER)

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
            self.country_code = position.country.lower()
            self.state_code = '{}-{}'.format(self.country_code, position.state.lower())
            self.state_name = position.state_long

        return cleaned_data

    def create_flight(self, is_staff):
        """
            The method will create a Flight model object and add it
            to the database.
        """
        new_flight = Flight()

        self.safe_flight(new_flight, is_staff)

    def safe_flight(self, flight, is_staff):
        """
            The method will fill and save the passed flight object.
        """

        # general
        species_name = self.cleaned_data.get('species')
        spotting_type = self.cleaned_data.get('spotting_type')
        date = self.cleaned_data.get('date')
        time = self.cleaned_data.get('time')
        comment = self.cleaned_data.get('comment')

        # location
        address = self.cleaned_data.get('address')

        # weather
        temperature = self.cleaned_data.get('temperature')
        temperature_unit = self.cleaned_data.get('temperature_unit')
        humidity = self.cleaned_data.get('humidity')
        wind_speed = self.cleaned_data.get('wind_speed')
        wind_speed_unit = self.cleaned_data.get('wind_speed_unit')


        # general
        flight.ant_species = AntSpecies.objects.get_or_create_with_name(species_name)
        flight.spotting_type = spotting_type
        flight.date = date
        flight.time = time
        flight.comment = comment

        # location
        flight.address = address
        flight.latitude = self.latitude
        flight.longitude = self.longitude

        flight.reviewed = is_staff

        # if flight.id is None:
        #     new_flight.full_clean()
        #     new_flight.save()

        # country = AntRegion.objects.get(code=self.country_code)
        # print(self.state_name)
        # state = AntRegion.objects.get_or_create(code=self.state_code, defaults={
        #     'name': self.state_name,
        #     'parent': country
        # })
        # new_flight.ant_regions.add(country, state) #pylint: disable=E1101


        # weather
        if temperature:
            if flight.temperature:
                flight.temperature.value = temperature
                flight.temperature.unit = temperature_unit
                flight.temperature.full_clean()
                flight.temperature.save()
            else:
                new_temperature = Temperature.objects.create(value=temperature, unit=temperature_unit)
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

        flight.full_clean()
        flight.save()
