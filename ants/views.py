from decimal import Decimal
from django.shortcuts import render

from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.views.generic.base import TemplateView

from django.db.models import Q

from .models import AntSize, AntSpecies, CommonName, ObsoleteName
from regions.models import Country, Region


# Create your views here.
class HomeView:
    pass


class AntSpeciesList(ListView):
    model = AntSpecies


class AntSpeciesSearch(TemplateView):
    template_name = 'ants/antspecies_list.html'

    def get_context_data(self, **kwargs):
        context = super(AntSpeciesSearch, self).get_context_data(**kwargs)
        search_term = self.request.GET.get('search_term')
        if search_term:
            object_list = AntSpecies.objects.filter(
                Q(name__icontains=search_term) |
                Q(commonname__name__icontains=search_term) |
                Q(obsoletename__name__icontains=search_term)).distinct()
            context['object_list'] = object_list
        context['search_term'] = search_term
        return context


class AntSpeciesDetail(DetailView):
    model = AntSpecies
    template_name = 'ants/antspecies_detail/antspecies_detail.html'

    def get_context_data(self, **kwargs):
        context = super(AntSpeciesDetail, self).get_context_data(**kwargs)

        ant = context['object']

        countries = Country.objects.filter(species=ant.id)
        regions = {}

        for country in countries:
            region_query = Region.objects.filter(country__code=country.code) \
                .filter(species__id=ant.id)

            if region_query:
                regions[country.code] = region_query

        context['countries'] = countries
        context['regions'] = regions

        common_names = ant.commonname_set.all()
        context['common_names'] = common_names

        old_names = ObsoleteName.objects.filter(species__id=ant.id)
        context['old_names'] = old_names
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
