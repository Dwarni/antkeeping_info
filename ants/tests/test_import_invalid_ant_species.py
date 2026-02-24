import datetime
from django.test import TestCase
from ants.models import AntSpecies, AntRegion
from flights.models import Flight
from ants.services.antwiki import import_invalid_ant_species

# Columns (tab-separated):
# 0: taxon_name, 1-7: (unused), 8: valid_name, 9: current_status
_INVALID_SPECIES_ROWS = [
    # Both species exist in DB → invalid species gets valid=False, flight reassigned
    "Acantholepis mamillatus\t\t\t\t\t\t\t\tIridomyrmex rufoniger\tsynonym",
    # Only invalid species exists → gets renamed to valid name
    "Acanthomyops negrensis\t\t\t\t\t\t\t\tLasiophanes atriventris\tsynonym",
    # status=homonym (not synonym) → skipped entirely, not added as invalid name
    "Acantholepis foreli\t\t\t\t\t\t\t\tStigmacros debilis\thomonym",
    # taxon_name has 2 spaces → skipped, not added as invalid name
    "Acantholepis frauenfeldi arnoldovi\t\t\t\t\t\t\t\tLepisiota semenovi\tsynonym",
]


class AntSpeciesManagerTestCase(TestCase):
    _invalid_species_name = 'Acantholepis mamillatus'
    _valid_species_name = 'Iridomyrmex rufoniger'
    _invalid_species_name_no_valid_species = 'Acanthomyops negrensis'
    _valid_species_name_no_valid_species = 'Lasiophanes atriventris'
    _species_name_with_holonym = 'Stigmacros debilis'
    _species_name_with_subspecies = 'Lepisiota semenovi'
    _flight1_id = None
    _flight2_id = None

    @classmethod
    def _create_objects(cls):
        iant = AntSpecies.objects.create(name=cls._invalid_species_name)
        AntSpecies.objects.create(name=cls._valid_species_name)

        cls._flight1_id = Flight.objects.create(
            ant_species=iant,
            spotting_type='Q',
            date=datetime.datetime.now(),
            address='95463 Bindlach, Germany',
            latitude=49.976655,
            longitude=11.618769,
            country=AntRegion.objects.create(
                name='Germany',
                code='de',
                type='Country')
        ).id

        iant2 = AntSpecies.objects.create(
            name=cls._invalid_species_name_no_valid_species)

        cls._flight2_id = Flight.objects.create(
            ant_species=iant2,
            spotting_type='Q',
            date=datetime.datetime.now(),
            address='Knoxville, TN 37920',
            latitude=49.976655,
            longitude=11.618769,
            country=AntRegion.objects.create(
                name='United States',
                code='us',
                type='Country')
        ).id

        AntSpecies.objects.create(name=cls._species_name_with_holonym)
        AntSpecies.objects.create(name=cls._species_name_with_subspecies)

    @classmethod
    def setUpTestData(cls):
        cls._create_objects()
        import_invalid_ant_species(_INVALID_SPECIES_ROWS)

    def test_set_invalid(self):
        iant = AntSpecies.objects.get(name=self._invalid_species_name)
        self.assertFalse(iant.valid)

    def test_renamed_invalid(self):
        self.assertFalse(AntSpecies.objects
                         .filter(name=self
                                 ._invalid_species_name_no_valid_species)
                         .exists())
        vant = AntSpecies.objects.get(
            name=self._valid_species_name_no_valid_species)
        self.assertTrue(vant.valid)

    def test_added_invalid_name(self):
        vant = AntSpecies.objects.get(name=self._valid_species_name)

        self.assertTrue(vant.invalid_names
                        .filter(name=self._invalid_species_name).exists())

    def test_homonym_not_added(self):
        vant = AntSpecies.objects.get(name=self._species_name_with_holonym)
        self.assertFalse(vant.invalid_names
                         .filter(name='Acantholepis foreli').exists())

    def test_sub_species_not_added(self):
        vant = AntSpecies.objects.get(name=self._species_name_with_subspecies)
        self.assertFalse(vant.invalid_names
                         .filter(name='Acantholepis frauenfeldi arnoldovi')
                         .exists())

    def test_flights_updated(self):
        f1 = Flight.objects.get(id=self._flight1_id)
        f2 = Flight.objects.get(id=self._flight2_id)

        self.assertEqual(f1.ant_species.name, self._valid_species_name)
        self.assertEqual(f2.ant_species.name,
                         self._valid_species_name_no_valid_species)
        self.assertIsNone(Flight.objects
                          .filter(ant_species__name=self._invalid_species_name)
                          .first())
        self.assertIsNone(
            Flight.objects
            .filter(
                ant_species__name=self._invalid_species_name_no_valid_species)
            .first())
