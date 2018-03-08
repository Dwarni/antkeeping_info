from ants.models import AntSize, AntSpecies, Genus


def genus_exists(name):
    return Genus.objects.filter(name=name).exists()


def get_genus(name):
    return Genus.objects.get(name=name)


def add_genus(name):
    new_genus = Genus(name=name)
    new_genus.full_clean()
    new_genus.save()
    return new_genus


def get_or_create_genus(name):
    if genus_exists(name):
        return get_genus(name)
    else:
        return add_genus(name)


def ant_exists(name):
    return AntSpecies.objects.filter(name=name).exists()


def get_ant(name):
    return AntSpecies.objects.get(name=name)


def get_genus_name(species_name):
    return species_name.split()[0]


def add_ant(name):
    new_ant = AntSpecies(name=name)
    new_ant.full_clean()
    genus_name = get_genus_name(name)
    genus = get_or_create_genus(genus_name)
    new_ant.genus = genus
    new_ant.save()
    return new_ant


def get_or_create_ant_species(name):
    if ant_exists(name):
        return get_ant(name)
    else:
        return add_ant(name)


def get_ants_by_country(code):
    ants = AntSpecies.objects.filter(countries__code=code)
    return ants


def get_ant_size(ant_id, type):
    size = AntSize.objects \
        .filter(ant_species__id=ant_id) \
        .filter(type=type) \
        .first()
    return size
