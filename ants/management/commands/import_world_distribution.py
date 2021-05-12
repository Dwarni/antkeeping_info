from ants.services.antwiki import import_world_distribution_csv
from ants.management.antwiki import AntwikiImportCommand


class Command(AntwikiImportCommand):
    def handle(self, *args, **options):
        import_world_distribution_csv(options['csv_file'], True)
