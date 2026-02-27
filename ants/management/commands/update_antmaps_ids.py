from django.core.management import BaseCommand

from ants.services.antmaps import update_antmaps_ids


class Command(BaseCommand):
    """
    The command adds/updates all antmaps region ids.
    """

    help = "Add/Update antmaps.org region ids."

    def handle(self, *args, **options):
        update_antmaps_ids()
