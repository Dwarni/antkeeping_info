from django.core.management import BaseCommand


class AntwikiImportCommand(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("csv_file", type=str)
