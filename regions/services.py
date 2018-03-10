from regions.models import Country, Region


def get_countries_with_ants(complete_only=False):
    query_set = Country.objects.filter(species__isnull=False)
    if complete_only:
        query_set = query_set.filter(ant_list_complete=True)
    query_set = query_set.distinct()
    return query_set


def get_regions_with_ants(country_code, complete_only=False):
    query_set = Region.objects.filter(country__code=country_code)
    query_set = query_set.filter(species__isnull=False)
    if complete_only:
        query_set = query_set.filter(ant_list_complete=True)
    return query_set
