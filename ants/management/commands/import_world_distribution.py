from ants.management.antwiki import AntwikiImportCommand
from ants.services.antwiki import import_world_distribution_csv


class Command(AntwikiImportCommand):
    def handle(self, *args, **options):
        import_world_distribution_csv(options["csv_file"], True)
