from django.core.management import BaseCommand
from flights.models import Flight


class Command(BaseCommand):
    """
        The command will collect flight months for all species based on
        the reported flights in database
    """
    help = 'Collects flight months for all ant species based on the reported '
    'flights'

    def add_arguments(self, parser):
        parser.add_argument('species_name', type=str)

    def handle(self, *args, **options):
        MINIMUM_FLIGHT_COUNT = 3
        species_name = options['species_name']
        flights = Flight.objects
        if species_name == 'all':
            flights = flights.all()
        else:
            flights = flights.filter(ant_species__name=species_name)
        flight_months_count = {}
        flight_months = {}

        for flight in flights:
            species_name = flight.ant_species.name

            if species_name not in flight_months_count:
                flight_months_count[species_name] = {}

            flight_months_dict = flight_months_count[species_name]

            flight_month = flight.date.month

            if flight_month in flight_months_dict:
                flight_months_dict[flight_month] += 1
            else:
                flight_months_dict[flight_month] = 1

        for species, months_dict in flight_months_count.items():
            flight_months[species] = []
            flight_months_list = flight_months[species]
            for month, months_count in months_dict.items():
                if months_count >= MINIMUM_FLIGHT_COUNT:
                    flight_months_list.append(month)

            flight_months_list.sort()

        print(flight_months_count)
        print(flight_months)
