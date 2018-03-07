from django.shortcuts import get_object_or_404, render, reverse
from regions.forms import AntlistForm
from regions.models import Country
from regions.services import get_countries_with_ants
from ants.services import get_ants_by_country


# Create your views here.
def index(request, country_code=None):
    ants = None
    country = None
    countries = get_countries_with_ants()
    if country_code is not None:
        country = get_object_or_404(Country, code=country_code)
        country_code = country_code.lower()
        ants = get_ants_by_country(country_code)

    url = request.build_absolute_uri(reverse('index'))

    return render(request, 'regions/countries.html', {
        'country_code': country_code,
        'country': country,
        'countries': countries,
        'ants': ants,
        'url': url
    })
