from django.core.exceptions import (
    ObjectDoesNotExist,
    MultipleObjectsReturned,
    ValidationError)
from django.db import transaction
import requests

from ants.models import AntRegion, AntSpecies, Distribution


def get_json(url):
    response = requests.get(url, verify=False)
    response.raise_for_status()
    return response.json()


def get_entities():
    return get_json('https://antmaps.org/api/v01/bentities.json')['bentities']


@transaction.atomic
def update_antmaps_ids():
        try:
            entities = get_entities()
            regions_updated = []
            regions_not_found = []
            multiple_regions = []
            for entity in entities:
                entity_display = entity['display']
                try:
                    ant_region = AntRegion.objects.get(name=entity_display)
                    ant_region.antmaps_id = entity['key']
                    ant_region.save()
                    regions_updated.append(entity_display)
                except ObjectDoesNotExist:
                    regions_not_found.append(entity_display)
                except MultipleObjectsReturned:
                    multiple_regions.append(entity_display)

            print('regions updated: {}, regions not found: {}, '
                  'multiple regions returned: {}'.format(
                    len(regions_updated),
                    len(regions_not_found),
                    len(multiple_regions)))
        except requests.exceptions.HTTPError as e:
            print('HTTP Error: {}'.format(e))
        except requests.exceptions.RequestException:
            print('Connection error')


def get_species(entity_id):
    species_json = get_json(
        ('https://antmaps.org/api/v01/species.json?bentity_id={}'
            .format(entity_id))
        )['species']
    return list(map(lambda s: s['display'], species_json))


def get_current_species(region):
    qs = (region.distribution
                .values('species__name'))
    species_list = list(map(lambda d: d['species__name'], qs))
    return species_list


@transaction.atomic
def add_or_update_distributions(region, ant_species_names):
    for ant_species_name in ant_species_names:
        try:
            ant_species = (
                AntSpecies
                .objects
                .get_or_create_with_name(ant_species_name))
            try:
                distribution = (Distribution.objects
                                .get(species=ant_species, region=region))
                distribution.native = True
                distribution.save()
            except ObjectDoesNotExist:
                Distribution.objects.create(
                    species=ant_species,
                    region=region,
                    native=True)
        except ValidationError:
            print(('{} is not a valid ant species name'
                   .format(ant_species_name)))


def update_species_of_regions(remove_species=False):
    for region in AntRegion.objects.filter(antmaps_id__isnull=False):
        print('Processing region: {} ...'.format(region.name))
        antmaps_species = get_species(region.antmaps_id)
        current_species = get_current_species(region)

        antmaps_species_set = set(antmaps_species)
        current_species_set = set(current_species)

        species_to_add = list(antmaps_species_set - current_species_set)
        species_updated = list(antmaps_species_set
                               .intersection(current_species_set))
        species_to_remove = list(current_species_set - antmaps_species_set)

        add_or_update_distributions(region, antmaps_species)
        print(' added {} species.'.format(len(species_to_add)))
        print(' updated {} species.'.format(len(species_updated)))
        print(' Species not on antmaps: {}'
              .format(', '.join(species_to_remove)))

        if remove_species:
            pass
