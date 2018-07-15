"""Module for managers of flights app."""
import calendar
from collections import OrderedDict
from django.db.models import Count, Manager, Q
from ants.models import AntSpecies

class FlightManager(Manager):
    """Manager for Flight model."""
    def flight_frequency_per_month(self, ant_species, country=None):
        """
            Return the frequency of flights per month for a specific ant species.
            The ant_species parameter can be the id, the slug or an object of type AntSpecies.
            If a country is provided the query will be restritcted to the specific country.
        """
        flights_qs = self.get_queryset()

        if isinstance(ant_species, str):
            flights_qs = flights_qs.filter(ant_species__slug=ant_species)
        elif isinstance(ant_species, AntSpecies) or isinstance(ant_species, int):
            flights_qs = flights_qs.filter(ant_species=ant_species)
        else:
            raise ValueError("ant_species must be an integer, a string or an object "
                             "of type AntSpecies""")

        frequency_aggregation = {
            month: Count('date', filter=Q(date__month=index + 1))
            for index, month in enumerate(calendar.month_name[1:])
        }

        aggregation_result = flights_qs.aggregate(**frequency_aggregation)
        ordered_result = OrderedDict()
        for i in range(1, 13):
            current_month = calendar.month_name[i]
            ordered_result[current_month] = aggregation_result[current_month]

        return ordered_result
