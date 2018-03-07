from decimal import Decimal
from ants.models import AntSize, AntSpecies


def create_size(
    type: str,
    minimum: Decimal,
    maximum: Decimal,
    ant_species: AntSpecies
):
    if minimum is not None or maximum is not None:
        AntSize.objects.create(
            type=type,
            minimum=minimum,
            maximum=maximum,
            ant_species=ant_species)


def convert_sizes(ant_species: AntSpecies):
    worker_size_min = ant_species.worker_size_min
    worker_size_max = ant_species.worker_size_max
    queen_size_min = ant_species.queen_size_min
    queen_size_max = ant_species.queen_size_max
    male_size_min = ant_species.male_size_min
    male_size_max = ant_species.male_size_max
    create_size(AntSize.WORKER, worker_size_min, worker_size_max, ant_species)
    create_size(AntSize.QUEEN, queen_size_min, queen_size_max, ant_species)
    create_size(AntSize.MALE, male_size_min, male_size_max, ant_species)
