from django.template.defaulttags import register
from ants.helpers import format_integer_range, \
    format_value as format_value_helper


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


@register.filter
def format_int_range(int_range, unit_symbol=None):
    return format_integer_range(int_range, unit_symbol)


@register.filter
def format_value(value, unit_symbol=None):
    return format_value_helper(value, unit_symbol)
