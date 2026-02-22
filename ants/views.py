"""
    Module for all models of ants app.
"""
import json
from dal import autocomplete
from django.core.paginator import Paginator

from django.shortcuts import redirect
from django.urls import reverse

from django.db import connection
from django.db.models import Count, F

from django.views.generic.detail import DetailView
from django.views.generic.base import TemplateView

from .models import AntRegion, AntSize, AntSpecies, Genus, Tribe, SubFamily
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


def ants_by_country(request, country):
    url = f'{reverse("taxonomic_ranks_by_region", args=["species"])}' \
            f'?country={country}'
    return redirect(url, permanent=True)


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
        taxonomic_rank_slug_field = 'slug'

        if taxonomic_rank == 'genera':
            taxonomic_rank_name_field = 'genus__name'
            taxonomic_rank_slug_field = 'genus__slug'
            taxonomic_rank_class = Genus

        if taxonomic_rank == 'tribes':
            taxonomic_rank_name_field = 'genus__tribe__name'
            taxonomic_rank_slug_field = 'genus__tribe__slug'
            taxonomic_rank_class = Tribe

        if taxonomic_rank == 'sub-families':
            taxonomic_rank_name_field = 'genus__tribe__sub_family__name'
            taxonomic_rank_slug_field = 'genus__tribe__sub_family__slug'
            taxonomic_rank_class = SubFamily

        if country:
            context['country'] = country
            country_obj = AntRegion.objects.get_by_id_or_code(country)
            if country_obj:
                context['country_name'] = country_obj.name
            sub_regions = AntRegion.states.with_ants_and_country(country) \
                .order_by('name')
            context['sub_regions'] = sub_regions

        if sub_region:
            context['sub_region'] = sub_region
            subregion_obj = AntRegion.objects.get_by_id_or_code(sub_region)
            if subregion_obj:
                context['subregion_name'] = subregion_obj.name
            taxonomic_ranks = AntSpecies.objects.by_region_code_or_id(
                sub_region
            ).select_related(
                'genus', 'genus__tribe', 'genus__tribe__sub_family'
            )

        if country and not sub_region:
            taxonomic_ranks = AntSpecies.objects.by_country_code(
                country
            ).select_related(
                'genus', 'genus__tribe', 'genus__tribe__sub_family'
            )

        context['countries'] = AntRegion.countries.with_ants()

        context['taxonomic_rank_type'] = taxonomic_rank_class._meta \
            .verbose_name_plural
        context['taxonomic_rank_type_lower'] = context['taxonomic_rank_type'] \
            .lower()

        if taxonomic_ranks:
            taxonomic_ranks = taxonomic_ranks \
                .annotate(taxonomic_rank_name=F(taxonomic_rank_name_field),
                          taxonomic_rank_slug=F(taxonomic_rank_slug_field))
            if name:
                context['name'] = name
                taxonomic_ranks = taxonomic_ranks \
                    .filter(taxonomic_rank_name__icontains=name)
            if taxonomic_rank == 'tribes':
                taxonomic_ranks = taxonomic_ranks \
                    .exclude(genus__tribe__name='')
            taxonomic_ranks = taxonomic_ranks.values('taxonomic_rank_name',
                                                     'taxonomic_rank_slug')
            taxonomic_ranks = taxonomic_ranks.distinct('taxonomic_rank_name') \
                .order_by('taxonomic_rank_name')
            paginator = Paginator(taxonomic_ranks, 50)
            page_number = self.request.GET.get('page')
            page_obj = paginator.get_page(page_number)
            context['page_obj'] = page_obj
            context['total_objects'] = taxonomic_ranks.count()

        add_iframe_to_context(context, self.request)
        return context


class Ranking(TemplateView):
    template_name = 'ants/antdb/ranking.html'
    num_entries = 50

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['num_entries'] = self.num_entries
        return context


class TopCountriesByNumberOfAntSpecies(Ranking):
    """Shows top countries by number of ant species."""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ranking = AntSpecies \
            .objects \
            .filter(distribution__region__type='Country') \
            .annotate(rank_entry_name=F('distribution__region__name')) \
            .values('rank_entry_name') \
            .annotate(total=Count('rank_entry_name')) \
            .order_by('-total')[:self.num_entries]
        context['ranking'] = ranking
        context['max_total'] = ranking[0]['total'] if ranking else 0
        context['heading'] = 'countries by number of ant species'
        return context


def dictfetchall(cursor):
    "Return all rows from a cursor as a dict"
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]


class TopCountriesByNumberOfAntGenera(Ranking):
    """Shows top countries by number of ant genera."""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ranking = None
        with connection.cursor() as cursor:
            cursor.execute(
                """
                    select rr.name as rank_entry_name,
                    count(distinct ag.name) as total
                    from ants_antspecies aa
                    inner join ants_species as2 on aa.species_ptr_id = as2.id
                    inner join ants_distribution ad ON as2.id = ad.species_id
                    inner join regions_region rr on rr.id = ad.region_id
                    inner join ants_antregion ar on ar.region_ptr_id = rr.id
                    inner join ants_genus ag on ag.id = as2.genus_id
                    where rr.type = 'Country'
                    group by rank_entry_name
                    order by total desc
                    limit %s
                """, [self.num_entries])
            ranking = dictfetchall(cursor)
        context['ranking'] = ranking
        context['max_total'] = ranking[0]['total'] if ranking else 0
        context['heading'] = 'countries by number of ant genera'
        return context


class TopAntSpeciesByNumberOfCountries(Ranking):
    """Shows top ant species by number of countries."""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ranking = AntSpecies \
            .objects \
            .filter(distribution__region__type='Country') \
            .annotate(
                rank_entry_name=F('name'),
                total=Count('distribution__region__name')
            ) \
            .values('rank_entry_name', 'total') \
            .order_by('-total')[:self.num_entries]
        context['ranking'] = ranking
        context['max_total'] = ranking[0]['total'] if ranking else 0
        context['heading'] = 'ant species by number of countries'
        return context


class TopAntGeneraByNumberOfCountries(Ranking):
    """Shows top ant genera by number of countries."""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ranking = None
        with connection.cursor() as cursor:
            cursor.execute(
                """
                    select ag.name as rank_entry_name,
                    count(distinct rr.code) as total
                    from ants_antspecies aa
                    inner join ants_species as2 on aa.species_ptr_id = as2.id
                    inner join ants_distribution ad ON as2.id = ad.species_id
                    inner join regions_region rr on rr.id = ad.region_id
                    inner join ants_antregion ar on ar.region_ptr_id = rr.id
                    inner join ants_genus ag on ag.id = as2.genus_id
                    where rr.type = 'Country'
                    group by rank_entry_name
                    order by total desc
                    limit %s
                """, [self.num_entries])
            ranking = dictfetchall(cursor)
        context['ranking'] = ranking
        context['max_total'] = ranking[0]['total'] if ranking else 0
        context['heading'] = 'ant genera by number of countries'
        return context


class TopAntGeneraByNumberOfSpecies(Ranking):
    """Shows top ant species by number of countries."""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ranking = Genus \
            .objects \
            .annotate(
                rank_entry_name=F('name'),
                total=Count('species')
            ) \
            .values('rank_entry_name', 'total') \
            .order_by('-total')[:self.num_entries]
        context['ranking'] = ranking
        context['max_total'] = ranking[0]['total'] if ranking else 0
        context['heading'] = 'ant genera by number of species'
        return context


class TopAuthorsByNumberOfAntSpecies(Ranking):
    """Shows top countries by number of ant species."""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ranking = AntSpecies \
            .objects \
            .annotate(rank_entry_name=F('author')) \
            .values('rank_entry_name') \
            .annotate(total=Count('rank_entry_name')) \
            .order_by('-total')[:self.num_entries]
        context['ranking'] = ranking
        context['max_total'] = ranking[0]['total'] if ranking else 0
        context['heading'] = 'authors by number of ant species'
        return context


class AntSpeciesDetail(DetailView):
    """Detail view of an ant species."""
    model = AntSpecies
    template_name = 'ants/antspecies_detail/antspecies_detail.html'

    def get_queryset(self):
        return super().get_queryset().select_related(
            'genus', 'genus__tribe', 'genus__tribe__sub_family'
        ).prefetch_related(
            'commonname_set', 'invalid_names', 'sizes', 'images'
        )

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
        """ regions = {}

        for country in countries:  # pylint: disable=E1133
            region_query = AntRegion.objects \
                .filter(parent__code=country.code) \
                .filter(distribution__species__id=ant.id)

            if region_query:
                regions[country.code] = region_query """

        context['countries'] = countries
        # context['regions'] = regions

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
