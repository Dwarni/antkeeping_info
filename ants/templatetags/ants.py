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


def _wiki_url(wiki_url, taxonomic_rank):
    taxonomic_rank = str(taxonomic_rank)
    full_wiki_url = None
    if taxonomic_rank:
        taxonomic_rank = taxonomic_rank.replace(' ', '_')
        full_wiki_url = f'{wiki_url}/{taxonomic_rank}'
    return full_wiki_url


@register.filter
def antwiki_url(taxonomic_rank_name: str) -> Union[str, None]:
    return _wiki_url('https://www.antwiki.org/wiki', taxonomic_rank_name)


@register.filter
def wikipedia_url(taxonomic_rank_name: str) -> Union[str, None]:
    return _wiki_url('https://en.wikipedia.org/wiki', taxonomic_rank_name)


@register.inclusion_tag("ants/antdb/tags/rank_entry.html")
def rank_entry(index: int, entry_name: str, entry_total: int, max_total: int):
    return {
        'index': index,
        'entry_name': entry_name,
        'entry_total': entry_total,
        'width': entry_total / max_total * 100
    }
