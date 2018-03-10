from django.shortcuts import get_object_or_404, render, reverse
from django.views.generic import ListView, TemplateView
from regions.forms import AntlistForm
from regions.models import Country
from regions.services import get_countries_with_ants
from ants.services import get_ants_by_country
from ants.models import AntSpecies


# Create your views here.
class CountryIndex(TemplateView):
    template_name = 'regions/countries.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['countries'] = get_countries_with_ants()
        return context


class CountryAntList(ListView):
    context_object_name = 'ants'
    template_name = 'regions/countries.html'

    def get_queryset(self):
        self.country_code = self.kwargs['country_code']
        self.country = get_object_or_404(Country, code=self.country_code)
        return get_ants_by_country(self.country_code)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['country_code'] = self.country_code
        context['country'] = self.country
        context['countries'] = get_countries_with_ants()
        context['url'] = self.request.build_absolute_uri(reverse('index'))
        return context
