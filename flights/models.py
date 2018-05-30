"""Module for models of flights app."""
from datetime import datetime
import geocoder

from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils.translation import ugettext as _

from taggit.managers import TaggableManager

from ants.models import AntSpecies, AntRegion
from .managers import FlightManager


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
    objects = FlightManager()
    # general
    ant_species = models.ForeignKey(
        AntSpecies,
        models.CASCADE,
        'flights'
    )
    FLIGHT = _('Nuptial Flight')
    FLIGHT_PREPERATION = _('Flight preparation')
    QUEEN_WINGLESS = _('Wingless (dealated) queen')
    QUEEN_WINGS = _('Winged (alate) queen')
    MALE = _('Male')

    SPOTTING_TYPE_CHOICES = (
        ('F', FLIGHT),
        ('FP', FLIGHT_PREPERATION),
        ('Q', QUEEN_WINGLESS),
        ('QW', QUEEN_WINGS),
        ('M', MALE)
    )

    SPOTTING_TYPE_CHOICES_DICT = dict(SPOTTING_TYPE_CHOICES)
    spotting_type = models.CharField(max_length=2, choices=SPOTTING_TYPE_CHOICES)
    date = models.DateField(validators=[
        MaxValueValidator(datetime.now().date(), _('Date has to be today or lie in the past.'))
    ])
    start_time = models.TimeField(blank=True, null=True)
    end_time = models.TimeField(blank=True, null=True)

    # location
    address = models.CharField(max_length=200)
    latitude = models.FloatField()
    longitude = models.FloatField()
    country = models.ForeignKey(
        AntRegion,
        models.CASCADE,
        'flights'
    )
    state_short = models.CharField(max_length=150, blank=True, null=True)
    state_long = models.CharField(max_length=150, blank=True, null=True)
    county = models.CharField(max_length=150, blank=True, null=True)
    city_short = models.CharField(max_length=150, blank=True, null=True)
    city_long = models.CharField(max_length=150, blank=True, null=True)
    habitat = TaggableManager(blank=True)

    @property
    def habitat_str(self):
        """Returns a comma seperated string containing all habitat tags."""
        return ', '.join(tag.name for tag in self.habitat.all())

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
    
    # rain
    NO_RAIN = ('NO', _('No recent rain'))
    RAIN_DURING = ('DURING', _('Rain during spotting'))
    RAIN_BEFORE = ('BEFORE', _('Rain before spotting'))
    RAIN_AFTER = ('AFTER', _('Rain after spotting'))
    RAIN_CHOICES = (
        NO_RAIN,
        RAIN_DURING,
        RAIN_BEFORE,
        RAIN_AFTER
    )
    RAIN_CHOICES_DICT = dict(RAIN_CHOICES)
    rain = models.CharField(
        max_length=6,
        choices=RAIN_CHOICES,
        blank=True,
        null=True
    )

    # sky condition
    CLEAR = ('CLEAR', _('Clear / Sunny'))
    MCLEAR = ('MCLEAR', _('Mostly Clear / Mostly Sunny'))
    PCLOUDY = ('PCLOUDY', _('Partly Cloudy / Partly Sunny'))
    MCLOUDY = ('MCLOUDY', _('Mostly Cloudy / Considerable Cloudiness'))
    CLOUDY = ('CLOUDY', _('Cloudy'))
    FAIR = ('FAIR', _('Fair'))
    SKY_CONDITION_CHOICES = (
        CLEAR,
        MCLEAR,
        PCLOUDY,
        MCLOUDY,
        CLOUDY,
        FAIR
    )
    SKY_CONDITION_CHOICES_DICT = dict(SKY_CONDITION_CHOICES)
    sky_condition = models.CharField(
        max_length=7,
        choices=SKY_CONDITION_CHOICES,
        blank=True,
        null=True
    )

    # additional information
    comment = models.TextField(max_length=255, blank=True, null=True)
    link = models.URLField(blank=True, null=True)

    reviewed = models.BooleanField(default=False)

    @property
    def spotting_type_verbose(self):
        """Returns the verbose string of the set spotting type."""
        return self.SPOTTING_TYPE_CHOICES_DICT[self.spotting_type]

    @property
    def time_str(self):
        """Returns a string representation of start and end time."""
        if self.start_time is None:
            return None
        if self.start_time == self.end_time or self.end_time is None:
            return self.start_time

        return '{} - {}'.format(self.start_time, self.end_time)


    @property
    def humidity_with_unit(self):
        """Returns the humidity value + unit as a string."""
        if self.humidity:
            return '{} %'.format(self.humidity)
        return None

    @property
    def rain_verbose(self):
        """Returns the verbose string of the set rain option."""
        return self.RAIN_CHOICES_DICT.get(self.rain, None)
    
    @property
    def sky_condition_verbose(self):
        """Returns the verbose string of the set sky condition option."""
        return self.SKY_CONDITION_CHOICES_DICT.get(self.sky_condition, None)

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

        # Check if at least a state was found
        if position.state is None:
            raise RuntimeError(_("""No state could be found. The address has to
                contain at least a state."""))

        self.address = position.address
        self.latitude = position.lat
        self.longitude = position.lng

        country_code = position.country.lower()
        self.country = AntRegion.objects.get(code=country_code)
        self.state_short = position.state
        self.state_long = position.state_long
        self.county = position.county
        self.city_short = position.city
        self.city_long = position.city_long

        self.full_clean()
        self.save()
