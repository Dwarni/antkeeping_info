"""Module for helper functions and classes in flights app."""
def format_unit(value, symbol):
    """Formats a unit value as a string including its symbol."""
    return '{:.1f} {}'.format(value, symbol)

def format_two_units(primary, secondary):
    """Formats two unit strings with the secondary unit displayed in brackets."""
    return '{} ({})'.format(primary, secondary)


class Temperature():
    """Class for storing and converting temperature."""
    CELSIUS = 'C'
    CELSIUS_SYMBOL = '°C'
    FAHRENHEIT = 'F'
    FAHRENHEIT_SYMBOL = '°F'
    CHOICES = (
        (CELSIUS, CELSIUS_SYMBOL),
        (FAHRENHEIT, FAHRENHEIT_SYMBOL)
    )
    def __init__(self, value, unit=CELSIUS):
        self.value = value
        self.unit = unit

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


class Velocity():
    """Class for storing and converting velocity."""
    KMH = 'KMH'
    KMH_SYMBOL = 'km/h'
    MPH = 'MPH'
    MPH_SYMBOL = 'mph'
    CHOICES = (
        (KMH, KMH_SYMBOL),
        (MPH, MPH_SYMBOL)
    )
    MPH_TO_KMH_FACTOR = 1.609344
    def __init__(self, value, unit=KMH):
        self.value = value
        self.unit = unit

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
