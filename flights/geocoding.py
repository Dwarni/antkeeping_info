"""
    Bing maps geocoding helper module.
"""
import requests

from django.conf import settings


def create_result_dict(raw_json):
    resource = raw_json['resourceSets'][0]['resources'][0]
    address = resource.get('address')
    full_address = resource.get('name')
    country = address.get('countryRegion')
    country_code = address.get('countryRegionIso2').lower()
    state = address.get('adminDistrict')
    postal_code = address.get('postalCode')
    city = address.get('locality')
    if postal_code:
        city = '{} {}'.format(postal_code, city)

    coordinates = resource['point']['coordinates']
    lat = coordinates[0]
    lng = coordinates[1]

    return {
        'address': full_address,
        'country': country,
        'country_code': country_code,
        'state': state,
        'city': city,
        'lat': lat,
        'lng': lng
    }

BASE_BING_URL = 'http://dev.virtualearth.net/REST/v1/Locations'


def geocode(query_string):
    """
        Request geocoding for specific query string.

        Return a dictionary containing the needed parts of the response.
    """
    url = BASE_BING_URL
    payload = {
        'q': query_string,
        'maxResults': 1,
        'incl': 'ciso2',
        'key': settings.BING_API_KEY_SERVER
    }

    response = requests.get(url, params=payload)
    return create_result_dict(response.json())


def reverse_geocode(lat, lng):
    """
        Request reverse geocoding for specitific latitude and longitude.

        Return a dictionary containing the needed parts of the response.
    """
    url = '{}/{},{}'.format(BASE_BING_URL, lat, lng)
    payload = {
        'maxResults': 1,
        'incl': 'ciso2',
        'key': settings.BING_API_KEY_SERVER
    }

    response = requests.get(url, params=payload)
    return create_result_dict(response.json())
