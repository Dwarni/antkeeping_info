from decimal import Decimal
from django.shortcuts import render, get_object_or_404, reverse

from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.views.generic.base import TemplateView

from django.db.models import Q

from .models import AntRegion, AntSize, AntSpecies, CommonName, InvalidName


# Create your views here.
class HomeView:
    pass


def add_iframe_to_context(context, request):
    iframe = request.GET.get('iframe', None)
    if iframe and iframe == 'true':
        context['iframe'] = True
    else:
        context['iframe'] = False


class AntList(ListView):
    context_object_name = 'ants'
    template_name = 'ants/ant_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        add_iframe_to_context(context, self.request)
        return context


class CountryIndex(TemplateView):
    template_name = 'ants/ant_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['countries'] = AntRegion.countries.with_ants()
        add_iframe_to_context(context, self.request)
        return context


class CountryAntList(AntList):
    def get_country(self):
        self.country_code = self.kwargs['country_code']
        self.country = get_object_or_404(AntRegion, code=self.country_code)

    def get_queryset(self):
        self.get_country()
        return AntSpecies.objects.by_country(self.country_code)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['country_code'] = self.country_code
        context['country'] = self.country
        context['ant_list_complete'] = self.country.ant_list_complete
        context['countries'] = AntRegion.countries.with_ants()
        regions = AntRegion.states.with_ants_and_country(self.country_code)
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
        self.region = get_object_or_404(AntRegion, code=self.region_code)
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


class AntSpeciesSearch(TemplateView):
    template_name = 'ants/antspecies_list.html'

    def get_context_data(self, **kwargs):
        context = super(AntSpeciesSearch, self).get_context_data(**kwargs)
        search_term = self.request.GET.get('search_term')
        if search_term:
            object_list = AntSpecies.objects.filter(
                Q(name__icontains=search_term) |
                Q(commonname__name__icontains=search_term) |
                Q(invalidname__name__icontains=search_term)).distinct()
            context['object_list'] = object_list
        context['search_term'] = search_term
        return context


class AntSpeciesDetail(DetailView):
    model = AntSpecies
    template_name = 'ants/antspecies_detail/antspecies_detail.html'

    def get_context_data(self, **kwargs):
        context = super(AntSpeciesDetail, self).get_context_data(**kwargs)

        ant = context['object']

        countries = AntRegion.countries.filter(distribution__species=ant.id)
        regions = {}

        for country in countries:
            region_query = AntRegion.objects \
                .filter(parent__code=country.code) \
                .filter(distribution__species__id=ant.id)

            if region_query:
                regions[country.code] = region_query

        context['countries'] = countries
        context['regions'] = regions

        common_names = ant.commonname_set.all()
        context['common_names'] = common_names

        invalid_names = InvalidName.objects.filter(species__id=ant.id)
        context['invalid_names'] = invalid_names
        worker_size = AntSize.objects.by_ant_and_type(ant.id, AntSize.WORKER)
        queen_size = AntSize.objects.by_ant_and_type(ant.id, AntSize.QUEEN)
        male_size = AntSize.objects.by_ant_and_type(ant.id, AntSize.MALE)

        context['worker_size'] = worker_size
        context['queen_size'] = queen_size
        context['male_size'] = male_size

        context
        return context


class NuptialFlight(TemplateView):
    template_name = 'ants/nuptial_flight.html'

    def get_context_data(self, **kwargs):
        context = super(NuptialFlight, self).get_context_data(**kwargs)
        ants = AntSpecies.objects.filter(nuptial_flight_start__isnull=False) \
            .filter(nuptial_flight_end__isnull=False)

        search_name = self.request.GET.get('name')
        context['search_name'] = search_name

        selected_country = kwargs['country'].lower()
        if not selected_country == 'ALL':
            ants = ants.filter(countries__code=selected_country)
            regions = Region.objects.filter(country__code=selected_country) \
                .filter(species__in=ants).distinct()
            context['regions'] = regions
            if('region' in kwargs):
                selected_region = kwargs['region'].upper()
                if not selected_region == 'ALL':
                    ants = ants \
                            .filter(regions__code=selected_region) \
                            .distinct()
                    context['region_code'] = selected_region

        if search_name:
            ants = ants.filter(
                Q(name__icontains=search_name) |
                Q(commonname__name__icontains=search_name) |
                Q(oldname__name__icontains=search_name)).distinct()

        countries = Country.objects.filter(
            species__antspecies__nuptial_flight_start__isnull="False"
            ).distinct()
        context['object_list'] = ants
        context['countries'] = countries
        context['country_code'] = kwargs['country']

        return context
