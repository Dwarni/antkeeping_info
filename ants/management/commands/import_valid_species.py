from ants.services.antwiki import import_valid_ant_species_csv
from ants.management.antwiki import AntwikiImportCommand


class Command(AntwikiImportCommand):
    def handle(self, *args, **options):
        import_valid_ant_species_csv(options['csv_file'], True)
