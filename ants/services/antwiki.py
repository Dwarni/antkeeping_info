from typing import Callable, Text, Iterable
import csv
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import transaction
from ants.models import AntSpecies, AntRegion, Distribution, Genus, \
    InvalidName, SubFamily, Tribe
from flights.models import Flight

_delimiter = '\t'


def _is_species_and_synonym(name: str, valid_name: str, status: str) -> bool:
    return name.count(' ') == 1 \
        and valid_name.count(' ') == 1 \
        and status == 'synonym'


def _import_from_csv(csv_file_path: str, import_function: Callable, verbose):
    csv_file = open(csv_file_path,
                    encoding="utf16") \
        .readlines()[1:]
    import_function(csv_file, verbose)


def _print_progress(species_name):
    # print(f'{species_name: <150}', end='\r', flush=True)
    print(f'{species_name: <150}')


def import_invalid_ant_species(csv_file: Iterable[Text], verbose=False):
    """
    Imports invalid ant species from given csv file.
    If the new species doesn't exist the existing species
    will be renamed.

    if the new species already exists, the invalid name
    will be added to list of invalid names.
    """
    with transaction.atomic():
        for line in csv.reader(csv_file, delimiter=_delimiter):
            taxon_name = line[0]
            valid_name = line[8]
            current_status = line[9]

            # only consider species (not sub species) and synonyms
            if not _is_species_and_synonym(
                    taxon_name,
                    valid_name,
                    current_status):
                continue

            if verbose:
                _print_progress(taxon_name)

            invalid_species = None
            valid_species = None
            # make species invalid if it exists in db
            try:
                invalid_species = AntSpecies.objects.get(name=taxon_name)
            except ObjectDoesNotExist:
                pass

            try:
                valid_species = AntSpecies.objects.get(name=valid_name)
            except ObjectDoesNotExist:
                pass

            # rename invalid species if valid species doesn't exist
            if invalid_species and not valid_species:
                invalid_species.name = valid_name
                invalid_species.save()

            # if both exist, invalidate old species (so it can be
            # manually checked)
            if invalid_species and valid_species:
                invalid_species.valid = False
                invalid_species.save()
                # update flights
                Flight.objects.filter(ant_species=invalid_species) \
                    .update(ant_species=valid_species)

            # Add new valid species if not existent
            valid_species = AntSpecies.objects \
                .get_or_create_with_name(valid_name)

            # Only add invalid name to list of invalid names if it wasn't
            # added yet
            if not valid_species.invalid_names.filter(
                    name=taxon_name).exists():
                InvalidName.objects.create(
                    name=taxon_name,
                    species_id=valid_species.id)


def import_invalid_ant_species_csv(csv_file: str, verbose: bool = False):
    _import_from_csv(csv_file, import_invalid_ant_species, verbose)


def import_valid_ant_species(csv_file: Iterable[Text], verbose=False):
    """
    Imports valid ant species from given csv file.
    Genera, Tribes and Sub families will also be created
    if they don't already exist.
    """
    with transaction.atomic():
        for line in csv.reader(csv_file, delimiter=_delimiter):
            sub_species = line[6]
            taxon_name = line[0]
            # antkeeping.info does not store sub species
            if sub_species or taxon_name.count(' ') > 1:
                continue
            else:
                sub_family = line[1]
                tribe = line[2]
                genus = line[3]
                species_group = line[4]
                author = line[8]
                year = line[9]

                if verbose:
                    _print_progress(taxon_name)

                try:
                    ant_species = AntSpecies.objects \
                        .get_or_create_with_name(taxon_name)
                except ValidationError as e:
                    print(taxon_name)
                    raise(e)
                if author:
                    ant_species.author = author
                if year:
                    ant_species.year = year
                if species_group:
                    ant_species.group = species_group
                ant_genus = Genus.objects.get_or_create_with_name(genus)
                ant_species.genus = ant_genus
                ant_species.save()
                ant_tribe = Tribe.objects.get_or_create_with_name(tribe)
                ant_genus.tribe = ant_tribe
                ant_genus.save()
                ant_sub_family = SubFamily.objects \
                    .get_or_create_with_name(sub_family)
                ant_tribe.sub_family = ant_sub_family
                ant_tribe.save()


def import_valid_ant_species_csv(csv_file: str, verbose: bool = False):
    _import_from_csv(csv_file, import_valid_ant_species, verbose)


def _add_distribution(species, region, introduced,
                      verbose: bool = False) -> None:
    d = Distribution.objects.filter(species=species, region=region).first()
    if not d:
        d = Distribution(species=species, region=region)
    d.native = introduced != 'Yes'
    d.save()
    if verbose:
        _print_progress(species.name)


def import_world_distribution(csv_file: Iterable[Text],
                              verbose: bool = False) -> None:
    """
    Imports distribution of ant species.
    """
    with transaction.atomic():
        for line in csv.reader(csv_file, delimiter=_delimiter):
            genus_name = line[1]
            species_name = line[2]
            sub_species = line[3]
            country_name = line[4]
            sub_region_name = line[5]
            occurence = line[6]

            if not species_name or sub_species:
                continue

            taxon_name = '{0} {1}'.format(genus_name, species_name)
            species = AntSpecies.objects.get_or_create_with_name(taxon_name)
            country = AntRegion.objects.find_by_name(country_name).first()

            if not country:
                country = AntRegion.objects.create(
                    name=country_name, type='Country')

            _add_distribution(species, country, occurence, verbose)

            if sub_region_name:
                sub_region = AntRegion.objects \
                    .find_by_name(sub_region_name).first()

                if not sub_region:
                    sub_region = AntRegion.objects.create(
                        name=sub_region_name, type='Subregion', parent=country
                    )

                _add_distribution(species, sub_region, occurence, verbose)


def import_world_distribution_csv(csv_file: str, verbose=False):
    _import_from_csv(csv_file, import_world_distribution, verbose)
