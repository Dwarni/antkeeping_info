from django.shortcuts import get_object_or_404, render, reverse
from django.views.generic import ListView, TemplateView
from regions.forms import AntlistForm
from regions.models import Country, Region
from regions.services import get_countries_with_ants, get_regions_with_ants
from ants.models import AntSpecies
from ants.views import AntList, add_iframe_to_context


# Create your views here.
class CountryIndex(TemplateView):
    template_name = 'ants/ant_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['countries'] = get_countries_with_ants()
        add_iframe_to_context(context, self.request)
        return context


class CountryAntList(AntList):
    def get_country(self):
        self.country_code = self.kwargs['country_code']
        self.country = get_object_or_404(Country, code=self.country_code)

    def get_queryset(self):
        self.get_country()
        return AntSpecies.objects.by_country(self.country_code)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['country_code'] = self.country_code
        context['country'] = self.country
        context['ant_list_complete'] = self.country.ant_list_complete
        context['countries'] = get_countries_with_ants()
        regions = get_regions_with_ants(self.country_code)
        context['regions'] = regions

        if regions.count() > 0:
            context['regions_type'] = regions[0].type

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
        self.get_country()
        query_set = AntSpecies.objects.by_region(
            code=self.region_code
        )
        return query_set

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['region_code'] = self.region_code
        context['region'] = self.region
        context['ant_list_complete'] = self.region.ant_list_complete
        return context
