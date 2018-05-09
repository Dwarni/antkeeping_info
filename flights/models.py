"""Module for models of flights app."""
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import ugettext as _
import geocoder

from ants.models import AntSpecies, AntRegion


# Create your models here.
def format_unit(value, symbol):
    """Formats a unit value as a string including its symbol."""
    return '{:.1f} {}'.format(value, symbol)

def format_two_units(primary, secondary):
    """Formats two unit strings with the secondary unit displayed in brackets."""
    return '{} ({})'.format(primary, secondary)

class Temperature(models.Model):
    """Temperature model."""
    CELSIUS = 'C'
    CELSIUS_SYMBOL = '°C'
    FAHRENHEIT = 'F'
    FAHRENHEIT_SYMBOL = '°F'
    UNIT_CHOICES = (
        (CELSIUS, CELSIUS_SYMBOL),
        (FAHRENHEIT, FAHRENHEIT_SYMBOL)
    )
    value = models.FloatField()
    unit = models.CharField(max_length=1, choices=UNIT_CHOICES)

    @property
    def celsius(self):
        """Returns the temperature in °C."""
        if self.unit == Temperature.CELSIUS:
            return self.value
        return (self.value - 32) / 1.8

    @property
    def celsius_str(self):
        """Returns the temperature in °C formatted as string including the unit symbol."""
        return format_unit(self.celsius, Temperature.CELSIUS_SYMBOL)

    @property
    def fahrenheit(self):
        """Returns the temperature in °F."""
        if self.unit == Temperature.FAHRENHEIT:
            return self.value
        return self.value * 1.8 + 32

    @property
    def fahrenheit_str(self):
        """Returns the temperature in °F formatted as string including the unit symbol."""
        return format_unit(self.fahrenheit, Temperature.FAHRENHEIT_SYMBOL)

    def __str__(self):
        if self.unit == Temperature.CELSIUS:
            return format_two_units(self.celsius_str, self.fahrenheit_str)
        return format_two_units(self.fahrenheit_str, self.celsius_str)

class Velocity(models.Model):
    """Velocity model."""
    KMH = 'KMH'
    KMH_SYMBOL = 'km/h'
    MPH = 'MPH'
    MPH_SYMBOL = 'mph'
    UNIT_CHOICES = (
        (KMH, KMH_SYMBOL),
        (MPH, MPH_SYMBOL)
    )
    MPH_TO_KMH_FACTOR = 1.609344
    value = models.FloatField(validators=[MinValueValidator(0)])
    unit = models.CharField(max_length=3, choices=UNIT_CHOICES)

    @property
    def kmh(self):
        """Returns the velocity in km/h."""
        if self.unit == Velocity.KMH:
            return self.value
        return self.value * Velocity.MPH_TO_KMH_FACTOR

    @property
    def kmh_str(self):
        """Returns the velocity in km/h formatted as string including the unit symbol."""
        return format_unit(self.kmh, Velocity.KMH_SYMBOL)

    @property
    def mph(self):
        """Returns the velocity in mph."""
        if self.unit == Velocity.MPH:
            return self.value
        return self.value / Velocity.MPH_TO_KMH_FACTOR

    @property
    def mph_str(self):
        """Returns the velocity in mph formatted as string including the unit symbol."""
        return format_unit(self.mph, Velocity.MPH_SYMBOL)

    def __str__(self):
        if self.unit == Velocity.KMH:
            return format_two_units(self.kmh_str, self.mph_str)
        return format_two_units(self.mph_str, self.kmh_str)


class Flight(models.Model):
    """Model class for ant flights."""
    # general
    ant_species = models.ForeignKey(
        AntSpecies,
        models.CASCADE,
        'flights'
    )
    FLIGHT = _('Nuptial Flight')
    QUEEN = _('Queen')
    SPOTTING_TYPE_CHOICES = (
        ('F', FLIGHT),
        ('Q', QUEEN)
    )
    SPOTTING_TYPE_CHOICES_DICT = dict(SPOTTING_TYPE_CHOICES)
    spotting_type = models.CharField(max_length=1, choices=SPOTTING_TYPE_CHOICES)
    date = models.DateField()
    time = models.TimeField(blank=True, null=True)
    comment = models.TextField(max_length=255, blank=True, null=True)

    # location
    address = models.CharField(max_length=100)
    latitude = models.FloatField()
    longitude = models.FloatField()
    ant_regions = models.ManyToManyField(
        AntRegion,
        'flights'
    )

    # weather
    temperature = models.OneToOneField(
        Temperature,
        models.CASCADE,
        related_name='flight',
        blank=True,
        null=True
    )
    humidity = models.IntegerField(
        blank=True,
        null=True,
        validators=[MinValueValidator(0)]
    )
    wind_speed = models.OneToOneField(
        Velocity,
        models.CASCADE,
        related_name='flight',
        blank=True,
        null=True
    )

    reviewed = models.BooleanField(default=False)

    @property
    def spotting_type_verbose(self):
        """Returns the verbose string of the set spotting type."""
        return self.SPOTTING_TYPE_CHOICES_DICT[self.spotting_type]

    @property
    def humidity_with_unit(self):
        """Returns the humidity value + unit as a string."""
        if self.humidity:
            return '{} %'.format(self.humidity)
        return None

    def __str__(self):
        return '{}: {}'.format(self.ant_species.name, self.address)

    def set_new_address(self, address):
        """
            Sets a new address. In the process additional information is queried
            via google geocoding api and needed information is stored in the model
            too.
        """
        if address is None:
            raise ValueError(_('Pass a valid address'))

        position = geocoder.google(address, key=settings.GOOGLE_API_KEY_SERVER)

        # Check if api returned a valid result
        if position.status != 'OK':
            raise RuntimeError(_('Did not receive a valid result from geocoding API'))

        # Check if at least a city was found
        if position.city is None:
            raise RuntimeError(_("""No city could be found. The address has to
                contain at least a city."""))

        self.address = position.address
        self.latitude = position.lat
        self.longitude = position.lng

        if self.id is None:
            self.full_clean()
            self.save()

        country_code = position.country.lower()
        state_code = '{}-{}'.format(country_code, position.state.lower())
        country = AntRegion.objects.get(code=country_code)
        state = AntRegion.objects.get(code=state_code)

        # First remove all existing regions
        self.ant_regions.clear() # pylint: disable=E1101

        # And add country and state to it
        self.ant_regions.add(country, state) # pylint: disable=E1101
        self.full_clean()
        self.save()
