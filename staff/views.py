import re

from django.db.models import Q
from django.views.generic import FormView

from ants.models import AntSpecies, AntRegion, Distribution

from .forms import AddAntspeciesToRegionForm

# Create your views here.
class AddAntspeciesToRegionView(FormView):
    form_class = AddAntspeciesToRegionForm
    template_name = 'staff/add_antspecies_to_region.html'
    success_url = '/'

    def form_valid(self, form):
        species = form.cleaned_data['species']
        region_id = form.cleaned_data['region']
        ant_region = AntRegion.objects.get(pk=region_id)

        for species_name in re.findall(r'[A-Z][a-z]+\s[a-z]+[\.]?', species):
            if '.' not in species_name:
                try:
                    ant_species = AntSpecies.objects.filter(
                        Q(name=species_name) | Q(invalidname__name=species_name)
                    ).first()
                    if not Distribution.objects.filter(
                            species=ant_species, region=ant_region
                        ).exists():
                        Distribution.objects.create(species=ant_species, region=ant_region)
                except AntSpecies.DoesNotExist:
                    print('Error with {}'.format(species_name))

        return super().form_valid(form)

