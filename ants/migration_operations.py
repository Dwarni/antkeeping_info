def add_generic_species_for_each_genus(apps, schema_editor=None):
    AntSpecies = apps.get_model("ants", "AntSpecies")
    Genus = apps.get_model("ants", "Genus")
    all_genera = Genus.objects.all()

    for genus in all_genera:
        species_name = genus.name + " sp."
        new_species = AntSpecies.objects.get_or_create_with_name(species_name, Genus)
        new_species.ordering = 0
        new_species.save()
