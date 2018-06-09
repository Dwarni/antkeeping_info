import re

from django.contrib import messages
from django.db.models import Q
from django.utils.translation import ugettext as _
from django.views.generic import FormView
from django.utils.decorators import method_decorator

from ants.models import AntSpecies, AntRegion, Distribution

from flights.views import staff_member_required

from .forms import AddAntspeciesToRegionForm

# Create your views here.
@method_decorator(staff_member_required, name='dispatch')
class AddAntspeciesToRegionView(FormView):
    form_class = AddAntspeciesToRegionForm
    template_name = 'staff/add_antspecies_to_region.html'
    success_url = '/'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def form_valid(self, form):
        species = form.cleaned_data['species']
        region_id = form.cleaned_data['region']
        ant_region = AntRegion.objects.get(pk=region_id)
        invalid_species = []
        added_species = []

        for species_name in re.findall(r'[A-Z][a-z]+\s[a-z]+[\.]?', species):
            if '.' not in species_name:
                ant_species = AntSpecies.objects.filter(
                    Q(name=species_name) | Q(invalidname__name=species_name)
                ).first()
                if not ant_species:
                    invalid_species.append(species_name)
                elif not Distribution.objects.filter(
                        species=ant_species, region=ant_region
                    ).exists():
                    Distribution.objects.create(species=ant_species, region=ant_region)
                    added_species.append(ant_species.name)

        if invalid_species:
            message_str = _('Could not add the following species: {}').format(
                ', '.join(invalid_species)
            )
            messages.warning(self.request, message_str)
        if added_species:
            messages.success(self.request, _('Added species: {} to region: {}'.format(', '.join(added_species), ant_region.name)))
        else:
            messages.warning(self.request, _('No species were added'))

        return super().form_valid(form)
