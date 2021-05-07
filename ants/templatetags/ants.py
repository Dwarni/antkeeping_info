from typing import Optional, Union
from django.template.defaulttags import register
from ants.helpers import format_integer_range, \
    format_value as format_value_helper


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


@register.filter
def format_int_range(int_range, unit_symbol: Optional[str] = None) -> str:
    return format_integer_range(int_range, unit_symbol)


@register.filter
def format_value(value: int, unit_symbol: Optional[str] = None) -> str:
    return format_value_helper(value, unit_symbol)


@register.filter
def antwiki_url(taxonomic_rank_name: str) -> Union[str, None]:
    antwiki_url = None
    if taxonomic_rank_name:
        antwiki_url = 'https://www.antwiki.org/wiki/{}' \
            .format(taxonomic_rank_name.replace(' ', '_'))
    return antwiki_url

@register.inclusion_tag("ants/antdb/tags/rank_entry.html")
def rank_entry(index: int, entry_name: str, entry_total: int, max_total: int):
    return {
        'index': index,
        'entry_name': entry_name,
        'entry_total': entry_total,
        'width': entry_total / max_total * 100
    }