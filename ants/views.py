from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from ants.models import AntSpecies
from regions.models import Country


# Create your views here.
def index(request):
    return render(request, 'layout.html')


def detail(request, ant_id):
    ant = get_object_or_404(AntSpecies, pk=ant_id)
    countries = Country.objects.filter(species__id=ant_id)
    return render(request, 'ants/ant_detail.html', {
        'ant': ant,
        'countries': countries,
    })
