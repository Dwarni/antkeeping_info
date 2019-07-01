from django.template.defaulttags import register
from flights.helpers import parse_hostname


@register.filter
def percentage(value, max_value):
    return (value / max_value) * 100
