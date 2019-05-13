"""
    Module for all models of ants app.
"""
import json
from dal import autocomplete
from django.shortcuts import get_object_or_404, reverse

from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.views.generic.base import TemplateView

from django.db.models import Q

from .models import AntRegion, AntSize, AntSpecies, InvalidName
from flights.models import Flight


# Create your views here.


def add_iframe_to_context(context, request):
    """
        Get's the 'iframe'-parameter and sets the 'iframe'
        key in the context dictionary accordingly.
    """
    iframe = request.GET.get('iframe', None)
    if iframe and iframe == 'true':
        context['iframe'] = True
    else:
        context['iframe'] = False


class AntList(ListView):
    """
        Generic view for all lists of ants.
    """
    context_object_name = 'ants'
    template_name = 'ants/ants_by_country/list.html'

    def get_context_data(self, **kwargs):  # pylint: disable=W0221
        context = super().get_context_data(**kwargs)
        add_iframe_to_context(context, self.request)
        return context


class CountryIndex(TemplateView):
    """Template view which get's a list of all countries with ants."""
    template_name = 'ants/ants_by_country/list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['countries'] = AntRegion.countries.with_ants()
        add_iframe_to_context(context, self.request)
        return context


class CountryAntList(AntList):
    """
        List view of ants of specific country.
        The view also queries a list of all regions of that country
        and in which ants occur.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.country = None

    def set_country(self):
        """
            Sets the country according to the 'country_code'
            parameter.
        """
        country_code = self.kwargs['country_code']
        self.country = get_object_or_404(AntRegion, code=country_code)

    def get_queryset(self):
        self.set_country()
        return AntSpecies.objects.by_country_code(self.country.code)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['country_code'] = self.country.code
        context['country'] = self.country
        context['ant_list_complete'] = self.country.ant_list_complete
        context['countries'] = AntRegion.countries.with_ants()
        regions = AntRegion.states.with_ants_and_country(self.country.code)
        context['regions'] = regions

        regions_count = regions.count()
        if regions_count > 0:
            # I pick the type of last entry since United states has one
            # district and otherwise states. If I picked first one it
            # would be labeled District, which is more wrong than
            # labeling just the single district as a state.
            context['regions_type'] = regions[regions_count - 1].type

        context['url'] = self.request.build_absolute_uri(reverse('index'))
        context['url_country'] = self.request.build_absolute_uri(
            reverse('country', kwargs={
                'country_code': context['country_code']
            })
        )
        return context


class RegionAntList(CountryAntList):
    """List view of ants of specific region."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.region = None

    def set_region(self):
        """
            Sets the region object according to the 'region_code'
            parameter.
        """
        region_code = self.kwargs['region_code']
        self.region = get_object_or_404(AntRegion, code=region_code)

    def get_queryset(self):
        self.set_region()
        self.set_country()
        query_set = AntSpecies.objects.by_region_code(
            code=self.region.code
        )
        return query_set

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['region_code'] = self.region.code
        context['region'] = self.region
        context['ant_list_complete'] = self.region.ant_list_complete
        return context


class AntSpeciesDetail(DetailView):
    """Detail view of an ant species."""
    model = AntSpecies
    template_name = 'ants/antspecies_detail/antspecies_detail.html'

    def __get_flight_frequency(self, ant_species):
        has_flights = Flight.objects.filter(ant_species=ant_species).exists()

        if has_flights:
            flight_frequency = Flight \
                                .objects \
                                .flight_frequency_per_month(ant_species)
            return json.dumps([value for key,
                               value in flight_frequency.items()],
                              separators=(',', ':'))

        return None

    def get_context_data(self, **kwargs):
        context = super(AntSpeciesDetail, self).get_context_data(**kwargs)

        ant = context['object']

        countries = AntRegion.countries.filter(distribution__species=ant.id)
        regions = {}

        for country in countries:  # pylint: disable=E1133
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
        context['flight_frequency'] = self.__get_flight_frequency(ant)

        return context


class AntSpeciesAutocomplete(autocomplete.Select2QuerySetView):
    """QuerySetView for flight habitat autocomplete."""

    def get_queryset(self):
        qs = AntSpecies.objects.filter(name__icontains=self.q)
        return qs
