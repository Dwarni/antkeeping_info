"""Module for importspecies command."""
from requests import get
from requests.exceptions import RequestException
from contextlib import closing
from bs4 import BeautifulSoup

from django.core.management import BaseCommand

from ants.models import AntRegion, AntSpecies, Distribution

def simple_get(url):
    """
    Attempts to get the content at `url` by making an HTTP GET request.
    If the content-type of response is some kind of HTML/XML, return the
    text content, otherwise return None
    """
    try:
        with closing(get(url, stream=True)) as resp:
            if is_good_response(resp):
                return resp.content
            else:
                return None

    except RequestException as request_exception:
        log_error('Error during requests to {0} : {1}'.format(url, str(request_exception)))
        return None


def is_good_response(resp):
    """
    Returns true if the response seems to be HTML, false otherwise
    """
    content_type = resp.headers['Content-Type'].lower()
    return (resp.status_code == 200
            and content_type is not None
            and content_type.find('html') > -1)


def log_error(error):
    """
    It is always a good idea to log errors.
    This function just prints them, but you can
    make it do anything.
    """
    print(error)

def add_distribution(species_name, country):
    species = AntSpecies.objects.get_or_create_with_name(species_name)
    if not species.distribution_set.filter(region=country).exists():
        Distribution.objects.create(species=species, region=country)
        return True
    return False

class Command(BaseCommand):
    """The command imports all species for a specific country from antwiki.org"""
    help = 'Imports ant species which occur in a country from antwiki.org'

    def add_arguments(self, parser):
        parser.add_argument('country_code', type=str)

    def handle(self, *args, **options):
        countries = None
        country_code = options['country_code']
        errors = []
        if country_code == 'all':
            # get all countries with not complete ant list
            countries = AntRegion.objects.filter(ant_list_complete=False,type='Country')
        else:
            countries = AntRegion.objects.filter(code=country_code)

        for country in countries:
            antwiki_url = 'http://www.antwiki.org/wiki/{}'.format(country.name)
            raw_html = simple_get(antwiki_url)
            if raw_html:
                html = BeautifulSoup(raw_html, 'html.parser')
                last_genus = None
                for element in html.select('li > i > a'):
                    splitted_text = element.text.split()
                    current_genus = splitted_text[0]
                    if last_genus is not None and current_genus < last_genus:
                        # In antwiki species which aren't native anymore are at the bottom
                        break

                    if len(splitted_text) == 2: # we don't want subspecies in antkeeping.info
                        print(element.text, sep=' ', end='', flush=True)
                        if add_distribution(' '.join(splitted_text), country):
                            print('...added')
                        else:
                            print('...existed')

                    last_genus = current_genus
                country.ant_list_complete = True
                country.save()
            else:
                error = 'Error getting species for Country: {}, URL: {} is not valid'.format(country.name, antwiki_url)
                errors.append(error)
                print(error)
        
        with open('import_species_errors', 'w') as error_file:
            for error in errors:
                error_file.write(error)




