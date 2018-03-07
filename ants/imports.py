import json
import pycountry
from ants.models import Country, Month, Region
from ants.services import get_or_create_ant_species


def import_countries():
    country_list = list(pycountry.countries)
    for country in country_list:
        code = country.alpha_2
        print('creating country {}'.format(code))
        Country.objects.create(code=country.alpha_2, name=country.name)


def import_states(country_code):
    country = Country.objects.get(code=country_code)
    states = list(pycountry.subdivisions.get(country_code=country_code))

    for state in states:
        print('creating region {}'.format(state.name))
        Region.objects.create(
            name=state.name,
            country=country,
            type=state.type
        )


def import_ant_sizes():
    with open('./ants/ant-sizes.json') as json_file:
        json_data = json_file.read()
        ants_json = json.loads(json_data)
        for ant_json in ants_json:
            print('processing {}'.format(ant_json['name']))
            ant_species = get_or_create_ant_species(ant_json['name'])
            ant_species.worker_size_min = ant_json['worker_size_min']
            ant_species.worker_size_max = ant_json['worker_size_max']
            ant_species.queen_size_min = ant_json['queen_size_min']
            ant_species.queen_size_max = ant_json['queen_size_max']
            ant_species.male_size_min = ant_json['male_size_min']
            ant_species.male_size_max = ant_json['male_size_max']
            ant_species.save()


def import_ant_countries():
    with open('./ants/ants-nuptial-flight.json') as json_file:
        json_data = json_file.read()
        ants_json = json.loads(json_data)
        for ant_json in ants_json:
            name = ant_json['name']
            countries = ant_json['countries']
            print('processing {}'.format(name))
            ant = get_or_create_ant_species(name)
            for country in countries:
                print('processing {}'.format(country['name']))
                ant.countries.add(Country.objects.get(code=country['code']))
            ant.save()


def import_ant_regions():
    with open('./ants/ants-nuptial-flight.json') as json_file:
        json_data = json_file.read()
        ants_json = json.loads(json_data)
        for ant_json in ants_json:
            name = ant_json['name']
            regions = ant_json['regions']
            print('processing {}'.format(name))
            ant = get_or_create_ant_species(name)
            for region in regions:
                print('processing {}'.format(region['name']))
                ant.countries.add(Country.objects.get(code=country['code']))
            ant.save()


def get_months_from_range(start, end):
    if start < 1 or end > 12:
        raise ValueError('start has to be greater or equal to 0 and end less \
        or equal to 12')
    if start <= end:
        return list(range(start, end + 1))
    else:
        months_list = []
        for month in range(start, 13):
            months_list.append(month)
        for month in range(1, end + 1):
            months_list.append(month)
        return months_list


def import_ant_nuptial_flights():
    with open('./ants/ants-nuptial-flight.json') as json_file:
        json_data = json_file.read()
        ants_json = json.loads(json_data)
        for ant_json in ants_json:
            name = ant_json['name']
            print('processing {}'.format(name))
            ant = get_or_create_ant_species(name)
            flight_start = ant_json['nuptial_flight_start']
            flight_end = ant_json['nuptial_flight_end']
            months = get_months_from_range(flight_start, flight_end)
            for month in months:
                ant.flight_months.add(Month.objects.get(pk=month))
