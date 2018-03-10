from django.shortcuts import get_object_or_404, render, reverse
from django.views.generic import ListView, TemplateView
from regions.forms import AntlistForm
from regions.models import Country, Region
from regions.services import get_countries_with_ants, get_regions_with_ants
from ants.services import get_ants_by_country
from ants.models import AntSpecies


# Create your views here.
class CountryIndex(TemplateView):
    template_name = 'regions/countries.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['countries'] = get_countries_with_ants()
        return context


class CountryAntList(ListView):
    context_object_name = 'ants'
    template_name = 'regions/countries.html'

    def get_queryset(self):
        self.country_code = self.kwargs['country_code']
        self.country = get_object_or_404(Country, code=self.country_code)
        return get_ants_by_country(self.country_code)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['country_code'] = self.country_code
        context['country'] = self.country
        context['countries'] = get_countries_with_ants()
        context['regions'] = get_regions_with_ants(self.country_code)
        context['url'] = self.request.build_absolute_uri(reverse('index'))
        context['url_country'] = self.request.build_absolute_uri(
            reverse('country', kwargs={
                'country_code': context['country_code']
            })
        )
        return context


class RegionAntList(CountryAntList):
    def get_queryset(self):
        self.region_code = self.kwargs['region_code']
        self.region = get_object_or_404(Region, code=self.region_code)
        query_set = super().get_queryset()
        query_set = query_set.filter(regions__code=self.region_code)
        return query_set

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['region_code'] = self.region_code
        context['region'] = self.region
        return context
