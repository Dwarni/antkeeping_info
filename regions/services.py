from regions.models import Country


def get_countries_with_ants(complete_only=False):
    query_set = Country.objects.filter(species__isnull=False)
    if complete_only:
        query_set = query_set.filter(ant_list_complete=True)
    query_set = query_set.distinct()
    return query_set
