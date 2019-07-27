from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.db import transaction
import requests

from ants.models import AntRegion


def get_json(url):
    response = requests.get(url, verify=False)
    response.raise_for_status()
    return response.json()


def get_antmaps_entities():
    return get_json('https://antmaps.org/api/v01/bentities.json')['bentities']


@transaction.atomic
def update_antmaps_ids():
        try:
            entities = get_antmaps_entities()
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