from django.template.defaulttags import register

from ants.helpers import format_integer_range
from ants.helpers import format_value as format_value_helper


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


@register.filter
def format_int_range(int_range, unit_symbol: str | None = None) -> str:
    return format_integer_range(int_range, unit_symbol)


@register.filter
def format_value(value: int, unit_symbol: str | None = None) -> str:
    return format_value_helper(value, unit_symbol)


def _wiki_url(wiki_url, taxonomic_rank):
    taxonomic_rank = str(taxonomic_rank)
    full_wiki_url = None
    if taxonomic_rank:
        taxonomic_rank = taxonomic_rank.replace(" ", "_")
        full_wiki_url = f"{wiki_url}/{taxonomic_rank}"
    return full_wiki_url


@register.filter
def antwiki_url(taxonomic_rank_name: str) -> str | None:
    return _wiki_url("https://www.antwiki.org/wiki", taxonomic_rank_name)


@register.filter
def wikipedia_url(taxonomic_rank_name: str) -> str | None:
    return _wiki_url("https://en.wikipedia.org/wiki", taxonomic_rank_name)


@register.simple_tag
def pagination_range(page_obj, wing=2):
    """Return a list of page numbers with None as ellipsis placeholder.

    Shows all pages when the total is <= 10; otherwise shows the first two,
    a window around the current page, and the last two pages, with None
    inserted wherever pages are skipped.
    """
    current = page_obj.number
    last = page_obj.paginator.num_pages

    if last <= 10:
        return list(range(1, last + 1))

    pages = set()
    pages.update(range(1, 3))                                          # always show 1-2
    pages.update(range(last - 1, last + 1))                           # always show last-1, last
    pages.update(range(max(1, current - wing), min(last, current + wing) + 1))

    result = []
    prev = None
    for p in sorted(pages):
        if prev is not None and p - prev > 1:
            result.append(None)  # ellipsis marker
        result.append(p)
        prev = p
    return result


@register.inclusion_tag("ants/antdb/tags/rank_entry.html")
def rank_entry(index: int, entry_name: str, entry_total: int, max_total: int):
    return {
        "index": index,
        "entry_name": entry_name,
        "entry_total": entry_total,
        "width": entry_total / max_total * 100,
    }


@register.simple_tag(takes_context=True)
def absolute_url(context, relative_or_absolute_url):
    """Converts a relative URL to an absolute URL using request.build_absolute_uri.

    If the URL is already absolute, it is returned unchanged.
    """
    if not relative_or_absolute_url:
        return ""
    url_str = str(relative_or_absolute_url)
    if url_str.startswith("http://") or url_str.startswith("https://"):
        return url_str
    request = context.get("request")
    if request:
        return request.build_absolute_uri(url_str)
    return url_str


@register.filter
def antmaps_species_url(species_name: str) -> str:
    """Returns the direct antmaps URL for a species."""
    if not species_name:
        return "https://antmaps.org/"
    formatted_name = str(species_name).strip().replace(" ", ".")
    return f"https://antmaps.org/?mode=species&species={formatted_name}"
