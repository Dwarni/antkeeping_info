from django.shortcuts import render, reverse
from regions.forms import AntlistForm
from ants.services import get_ants_by_country


# Create your views here.
def index(request, country_code=None):
    ants = None
    if country_code is not None:
        country_code = country_code.lower()
        ants = get_ants_by_country(country_code)

    form = AntlistForm(country_code)
    url = request.build_absolute_uri(reverse('index'))

    return render(request, 'regions/countries.html', {
        'form': form,
        'ants': ants,
        'url': url
    })
