from django.core.management import BaseCommand

from ants.services.antmaps import update_species_of_regions


class Command(BaseCommand):
    """
    The command adds/updates all distributions according to antmaps.
    Currently the command won't remove any species from regions they
    are not native to according to antmaps.
    """

    help = "Add/Update antmaps.org distribution"

    def handle(self, *args, **options):
        update_species_of_regions()
