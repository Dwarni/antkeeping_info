"""
    Module for all models of ants app.
"""
import json
from dal import autocomplete
from django.core.paginator import Paginator

from django.db.models import F

from django.views.generic.detail import DetailView
from django.views.generic.base import TemplateView

from .models import AntRegion, AntSize, AntSpecies, Genus, SubFamily
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


class TaxonomicRanksByRegion(TemplateView):
    """Let user see which ant species occur in selected regions."""
    template_name = 'ants/antdb/ant_species_by_region.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        taxonomic_rank = kwargs.get('taxonomic_rank')

        country = self.request.GET.get('country')
        sub_region = self.request.GET.get('subRegion')
        name = self.request.GET.get('name')
        taxonomic_ranks = None
        taxonomic_rank_class = AntSpecies
        taxonomic_rank_name_field = 'name'

        if taxonomic_rank == 'genera':
            taxonomic_rank_name_field = 'genus__name'
            taxonomic_rank_class = Genus

        if taxonomic_rank == 'sub-families':
            taxonomic_rank_name_field = 'genus__sub_family__name'
            taxonomic_rank_class = SubFamily

        if country:
            context['country'] = country
            sub_regions = AntRegion.states.with_ants_and_country(country)
            context['sub_regions'] = sub_regions

        if sub_region:
            context['sub_region'] = sub_region
            taxonomic_ranks = AntSpecies.objects.by_region_code(
                code=sub_region)

        if country and not sub_region:
            taxonomic_ranks = AntSpecies.objects.by_country_code(country)

        context['countries'] = AntRegion.countries.with_ants()

        context['taxonomic_rank_type'] = taxonomic_rank_class._meta.verbose_name_plural
        context['taxonomic_rank_type_lower'] = context['taxonomic_rank_type'].lower()

        if taxonomic_ranks:
            taxonomic_ranks = taxonomic_ranks.annotate(taxonomic_rank_name=F(taxonomic_rank_name_field))
            if name:
                context['name'] = name
                taxonomic_ranks = taxonomic_ranks.filter(taxonomic_rank_name__icontains=name)
            taxonomic_ranks = taxonomic_ranks.values('taxonomic_rank_name')
            taxonomic_ranks = taxonomic_ranks.distinct('taxonomic_rank_name').order_by('taxonomic_rank_name')
            paginator = Paginator(taxonomic_ranks, 50)
            page_number = self.request.GET.get('page')
            page_obj = paginator.get_page(page_number)
            context['page_obj'] = page_obj
            context['total_objects'] = taxonomic_ranks.count()

        add_iframe_to_context(context, self.request)
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

        common_names = ant.common_names.all()
        context['common_names'] = common_names

        invalid_names = ant.invalid_names.all()
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
