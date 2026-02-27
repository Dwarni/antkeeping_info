"""Test module for helper functions and classes in flights app."""

from django.test import TestCase

from flights.helpers import Temperature, Velocity


class TemperatureTest(TestCase):
    """Tests for the Temperature class"""

    def test_create_without_unit(self):
        """Test for creating a Temperature object without specifying a unit."""
        temp_value = 25
        temp = Temperature(temp_value)
        self.assertEqual(temp.value, temp_value)
        self.assertEqual(temp.unit, Temperature.CELSIUS)

    def test_create_with_unit(self):
        """Test for creating a Temperature object with specifying a unit."""
        celsius_value = 25
        celsius = Temperature(celsius_value, Temperature.CELSIUS)
        self.assertEqual(celsius.unit, Temperature.CELSIUS)
        self.assertEqual(celsius_value, celsius.value)
        self.assertEqual(celsius_value, celsius.celsius)

        fahrenheit_value = 77
        fahrenheit = Temperature(fahrenheit_value, Temperature.FAHRENHEIT)
        self.assertEqual(fahrenheit.unit, Temperature.FAHRENHEIT)
        self.assertEqual(fahrenheit_value, fahrenheit.value)
        self.assertEqual(fahrenheit_value, fahrenheit.fahrenheit)

    def test_convert_to_fahrenheit(self):
        """Test for conversion to Fahrenheit."""
        temp = Temperature(25)
        self.assertEqual(temp.fahrenheit, 77)

    def test_convert_to_celsius(self):
        """Test for conversion to Celsius."""
        temp = Temperature(104, Temperature.FAHRENHEIT)
        self.assertEqual(temp.celsius, 40)

    def test_str_output(self):
        """Test for formatted string output."""
        celsius = Temperature(25)
        fahrenheit = Temperature(104, Temperature.FAHRENHEIT)
        self.assertEqual("25.0 ℃ (77.0 ℉)", str(celsius))
        self.assertEqual("104.0 ℉ (40.0 ℃)", str(fahrenheit))


class VelocityTest(TestCase):
    """Tests for the Velocity class."""

    def test_create_without_unit(self):
        """Test for creating a Velocity object without specifying a unit."""
        vel_value = 80
        vel = Velocity(vel_value)
        self.assertEqual(vel.value, vel_value)
        self.assertEqual(vel.unit, Velocity.KMH)

    def test_create_with_unit(self):
        """Test for creating a Velocity object with specifying a unit."""
        vel_kmh_value = 80
        vel_mph_value = 49.7097

        vel_kmh = Velocity(vel_kmh_value, Velocity.KMH)
        self.assertEqual(vel_kmh.unit, Velocity.KMH)
        self.assertEqual(vel_kmh.value, vel_kmh_value)
        self.assertAlmostEqual(vel_kmh.mph, vel_mph_value, 4)

        vel_mph = Velocity(vel_mph_value, Velocity.MPH)
        self.assertEqual(vel_mph.unit, Velocity.MPH)
        self.assertEqual(vel_mph.value, vel_mph_value)
        self.assertAlmostEqual(vel_mph.kmh, vel_kmh_value, 0)

    def test_convert_to_mph(self):
        """Test conversion to mph."""
        vel = Velocity(30)
        self.assertAlmostEqual(vel.mph, 18.6411, 4)

    def test_convert_to_kmh(self):
        """Test conversion to kmh."""
        vel = Velocity(60, Velocity.MPH)
        self.assertAlmostEqual(vel.kmh, 96.5606, 4)

    def test_str_output(self):
        """Test for formatted string output."""
        vel_kmh = Velocity(60)
        vel_mph = Velocity(40, Velocity.MPH)

        self.assertEqual("60.0 km/h (37.3 mph)", str(vel_kmh))
        self.assertEqual("40.0 mph (64.4 km/h)", str(vel_mph))
