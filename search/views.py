"""Module for views of search app."""
from django.views.generic import TemplateView
from django.db.models import Q

from ants.models import AntRegion, AntSpecies

# Create your views here.


class SearchView(TemplateView):
    """
        Search view.
        The view will either display a list of search results or if only
        a single result was found redirect to the detail page.
    """
    template_name = 'search/search_results.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query_string = self.request.GET.get('q', None)
        query_string = query_string.replace('+', ' ')

        ant_species = AntSpecies.objects.search_by_name(query_string)

        context['ant_species'] = ant_species

        regions = AntRegion.objects.filter(
            Q(distribution__isnull=False),
            Q(code__icontains=query_string) |
            Q(name__icontains=query_string) |
            Q(official_name__icontains=query_string) |
            Q(antwiki_name__icontains=query_string)
        ).distinct()
        context['regions'] = regions

        context['query_string'] = query_string
        return context
