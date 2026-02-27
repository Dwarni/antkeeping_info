from django.http import JsonResponse

from flights.models import Flight

"""
    Return the years in which nuptial flights occured.
"""


def years(request):
    dates = [d.year for d in Flight.objects.all().dates("date", "year", order="DESC")]
    return JsonResponse(dates, safe=False)


"""
    Return the ant flights in a specific year.
    If no year was passed all are returned.
"""


def flights(request):
    year = request.GET.get("year")
    flights = Flight.objects.all()

    if year is not None:
        flights = flights.filter(date__year=year)

    flights = flights.values("id", "latitude", "longitude", "ant_species__name", "date")
    data = [
        {
            "id": flight.get("id"),
            "position": {"lat": flight.get("latitude"), "lng": flight.get("longitude")},
            "ant": flight.get("ant_species__name"),
            "date": flight.get("date"),
        }
        for flight in flights
    ]

    return JsonResponse(data, safe=False)
