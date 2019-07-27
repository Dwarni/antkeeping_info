"""
    This module contains all models for ants app.
"""
from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator, \
    RegexValidator, ValidationError
from django.db import models
from django.contrib.postgres import validators as psql_validators
from django.contrib.postgres import fields as psql_fields
from django.utils.text import slugify
from django.utils.translation import ugettext as _
from django.urls import reverse

from sorl.thumbnail import ImageField

from regions.models import Region
from ants.managers import AntRegionManager, CountryAntRegionManager, \
    AntSizeManager, AntSpeciesManager, GenusManager, StateAntRegionManager
from ants.helpers import format_integer_range, DEFAULT_NONE_STR


# Create your models here.

LANG_CHOICES = sorted(
    [(lang_code, _(lang_name)) for lang_code, lang_name in settings.LANGUAGES],
    key=lambda language: language[1])


class SpeciesDescription(models.Model):
    """A textual description of an ant species"""
    language = models.CharField(max_length=7, choices=LANG_CHOICES)
    description = models.TextField()
    species = models.ForeignKey('Species', on_delete=models.CASCADE)


class TaxonomicRankMeta:
    """Base meta class for all Taxonomic rank models"""
    ordering = ['name']


class TaxonomicRank(models.Model):
    """
        Abstract base class for all taxonomic rank models.
    """
    name = models.CharField(
        db_index=True,
        max_length=100,
        unique=True,
        validators=[
            RegexValidator('^[A-Z][a-z]+$')
        ]
    )
    slug = models.SlugField(db_index=True, editable=False)

    class Meta:
        abstract = True

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        self.slug = slugify(self.name)
        super().save(force_insert, force_update, using,
                     update_fields)

    def __str__(self):
        return self.name


class Family(TaxonomicRank):
    """Model which represents a taxonomic rank of type 'Family'."""
    class Meta(TaxonomicRankMeta):
        verbose_name = _('Family')
        verbose_name_plural = _('Families')


class SubFamily(TaxonomicRank):
    """Model which represents a taxonomic rank of type 'Subfamily'."""
    family = models.ForeignKey(
        Family,
        models.SET_NULL,
        blank=True,
        null=True
    )

    class Meta(TaxonomicRankMeta):
        verbose_name = _('Sub Family')
        verbose_name_plural = _('Sub Families')


class Genus(TaxonomicRank):
    """Model which represents a taxonomic rank of type 'Genus'."""
    sub_family = models.ForeignKey(
        SubFamily,
        models.SET_NULL,
        blank=True,
        null=True
    )

    objects = GenusManager()

    class Meta(TaxonomicRankMeta):
        verbose_name_plural = _('Genera')


class AntRegion(Region):
    """
        A model which describes a region in which ants may live.
    """
    objects = AntRegionManager()
    countries = CountryAntRegionManager()
    states = StateAntRegionManager()
    """
        Contains the region name antwiki is using in case it is different
        to name.
    """
    antwiki_name = models.CharField(max_length=200, blank=True, null=True)
    ant_list_complete = models.BooleanField(default=False)
    antmaps_id = models.CharField(
        db_index=True,
        max_length=10,
        blank=True,
        null=True,
        help_text=_('The id of the region used by antmaps.org.')
    )

    def get_absolute_url(self):
        if self.type == 'Country':
            return reverse('country', args=[self.code])

        return reverse('region', args=[self.parent.code, self.code])

    @property
    def antwiki_url(self):
        """Returns the url to the antwiki.org page for that region."""
        country_name = self.name
        if self.antwiki_name:
            country_name = self.antwiki_name
        return 'http://www.antwiki.org/wiki/{}' \
            .format(country_name.replace(' ', '_'))


class Distribution(models.Model):
    """
        A model which describes the destribution of an ant species.
    """
    species = models.ForeignKey(
        'AntSpecies',
        related_name='distribution',
        on_delete=models.CASCADE
    )
    region = models.ForeignKey(
        'AntRegion',
        related_name='distribution',
        on_delete=models.CASCADE
    )
    native = models.NullBooleanField(
        blank=True,
        null=True,
        verbose_name=_('Native')
    )
    protected = models.NullBooleanField(
        blank=True,
        null=True,
        verbose_name=_('Protected by law')
    )
    NOT_ON_RED_LIST = 'NOT_ON_RED_LIST'
    LEAST_CONCERN = 'LEAST_CONCERN'
    NEAR_THREATENED = 'NEAR_THREATENED'
    VULNERABLE = 'VULNERABLE'
    ENDANGERED = 'ENDANGERED'
    CRITICALLY_ENDANGERED = 'CRITICALLY_ENDANGERED'
    EXTINCT_IN_WILD = 'EXTINCT_IN_WILD'
    EXTINCT = 'EXTINCT'
    RED_LIST_CHOICES = (
        (NOT_ON_RED_LIST, _('Not on red list')),
        (LEAST_CONCERN, _('Least Concern')),
        (NEAR_THREATENED, _('Near Threatened')),
        (VULNERABLE, _('Vulnerable')),
        (ENDANGERED, _('Endangered')),
        (CRITICALLY_ENDANGERED, _('Critically Endangered')),
        (EXTINCT_IN_WILD, _('Extinct in the Wild')),
        (EXTINCT, _('Extinct'))
    )
    red_list_status = models.TextField(
        max_length=40,
        blank=True,
        null=True,
        choices=RED_LIST_CHOICES
    )

    def __str__(self):
        return str(self.region)


class SpeciesMeta(TaxonomicRankMeta):
    verbose_name = _('Species')
    verbose_name_plural = _('Species')
    ordering = ('genus__name', 'ordering', 'name')


class Species(TaxonomicRank):
    """Model which represents a taxonomic rank of type 'Species'."""
    name_validators = [
        RegexValidator(
            '^[A-Z][a-z]+ [a-z\\.]+$',
            _("""Enter a valid species name.""")
        )
    ]
    name = models.CharField(
        db_index=True,
        max_length=100,
        unique=True,
        validators=name_validators)
    genus = models.ForeignKey(
        Genus,
        models.SET_NULL,
        blank=True,
        null=True
    )
    ordering = models.IntegerField(
        db_index=True,
        default=1
    )

    @property
    def name_underscore(self):
        """Returns the species name with an underscore instead of a space."""
        return self.name.replace(" ", "_")

    @property
    def common_names(self):
        """
            Return query set which contains all common names of the specific
            species.
        """
        return self.commonname_set.all()

    @property
    def common_names_str(self):
        """
            Return all common names of the specific species seperated by ','.
        """
        if self.common_names.exists():
            return ', '.join(str(name) for name in self.common_names)
        else:
            return DEFAULT_NONE_STR
    
    @property
    def invalid_names_str(self):
        """
            Return all invalid names of the specific species seperated by ','.
        """
        if self.invalid_names.exists():
            return ', '.join(str(name) for name in self.invalid_names.all())
        else:
            return DEFAULT_NONE_STR

    class Meta(SpeciesMeta):
        pass


class SizeField(models.DecimalField):
    """Field which stores the size of an ant."""
    MAX_DIGITS = 6
    MAX_DECIMAL_PLACES = 2
    MIN_SIZE = Decimal('0.01')

    def __init__(self, *args, **kwargs):
        kwargs['max_digits'] = self.MAX_DIGITS
        kwargs['decimal_places'] = self.MAX_DECIMAL_PLACES
        kwargs['null'] = True
        kwargs['blank'] = True
        kwargs['validators'] = [
            MinValueValidator(self.MIN_SIZE)
        ]
        super().__init__(*args, **kwargs)


class Month(models.Model):
    """Model which represents a month"""
    name = models.CharField(max_length=50, db_index=True)

    def __str__(self):
        return _(self.name)

    class Meta:
        ordering = ['id']


class AntSize(models.Model):
    """Model which stores size information for a specific ant."""
    WORKER = 'WORKER'
    QUEEN = 'QUEEN'
    MALE = 'MALE'
    ANT_TYPE_CHOICES = (
        (WORKER, _('Worker')),
        (QUEEN, _('Queen')),
        (MALE, _('Male')),
    )
    ANT_SIZE_STRINGS = {
        WORKER: _('Worker size'),
        QUEEN: _('Queen size'),
        MALE: _('Male size'),
    }
    type = models.CharField(
        max_length=20,
        db_index=True,
        choices=ANT_TYPE_CHOICES
    )
    minimum = SizeField(verbose_name=_('Minimum (mm)'))
    maximum = SizeField(verbose_name=_('Maximum (mm)'))
    ant_species = models.ForeignKey('AntSpecies', related_name='sizes',
                                    on_delete=models.CASCADE)

    @staticmethod
    def calc_img_width(size):
        """Calculates the image with based on the size."""
        factor = Decimal(1.16959)
        if size:
            return size * factor
        return None

    def minimum_img(self):
        """Returns the width of the image for minimum size."""
        return self.calc_img_width(self.minimum)

    def maximum_img(self):
        """Returns the width of the image for maximum size."""
        return self.calc_img_width(self.maximum)

    def clean(self):
        if self.minimum > self.maximum:
            raise ValidationError(
                _('Minimum size may not be greater than maximum size!')
            )

    def __str__(self):
        return self.ANT_SIZE_STRINGS.get(self.type)

    objects = AntSizeManager()


INT_RANGE_HELP_TEXT = _('Note that the upper value is not included '
                        'so if you want to enter 25 - 28 you have '
                        'to enter 25 - 29')


class AntSpecies(Species):
    """Model of an ant species."""
    # colony
    MONOGYNOUS = 'MONO'
    POLYGYNOUS = 'POLY'
    OLIGOGYNOUS = 'OLIGO'

    COLONY_STRUCTURE_CHOICES = (
        (MONOGYNOUS, _('Monogynous')),
        (OLIGOGYNOUS, _('Oligogynous')),
        (POLYGYNOUS, _('Polygynous'))
    )

    colony_structure = models.CharField(
        max_length=4,
        blank=True,
        null=True,
        choices=COLONY_STRUCTURE_CHOICES,
        verbose_name=_('Colony Structure')
    )

    @property
    def colony_structure_str(self):
        """Returns the colony structure as a string."""
        if self.colony_structure is None:
            return DEFAULT_NONE_STR
        else:
            return dict(self.COLONY_STRUCTURE_CHOICES)[self.colony_structure]

    worker_polymorphism = models.NullBooleanField(
        blank=True,
        null=True,
        verbose_name=_('Worker polymorphism')
    )

    # founding
    CLAUSTRAL = 'c'
    SEMI_CLAUSTRAL = 'sc'
    SOCIAL_PARASITIC = 'sp'
    SOCIAL_PARASITIC_CAN_OPEN_PUPAE = 'spp'

    FOUNDING_CHOICES = (
        (CLAUSTRAL, _('claustral (queen does not need any food)')),
        (SEMI_CLAUSTRAL, _('semi-claustral (queen needs to be fed during '
                           'founding)')),
        (SOCIAL_PARASITIC, _('social parasitic (queen needs workers of '
                             'suitable ant species)')),
        (SOCIAL_PARASITIC_CAN_OPEN_PUPAE,
            _('social parasitic (founding can be '
              'done with pupae of suitable ant species)'))
    )

    founding = models.CharField(
        max_length=3,
        blank=True,
        null=True,
        choices=FOUNDING_CHOICES,
        verbose_name=_('Founding')
    )

    flight_months = models.ManyToManyField(
        Month,
        blank=True,
        verbose_name=_('Nuptial flight months'),
    )

    flight_hour_range = psql_fields.IntegerRangeField(
        blank=True,
        null=True,
        verbose_name=_('Flight hour range'),
        validators=[
            psql_validators.RangeMinValueValidator(1),
            psql_validators.RangeMaxValueValidator(25)],
        help_text=INT_RANGE_HELP_TEXT
    )

    MODERATE = 'm'
    WARM = 'w'
    STICKY = 's'
    FLIGHT_CLIMATE_CHOICES = (
        (MODERATE, _('Moderate temperature')),
        (WARM, _('Warm temperature')),
        (STICKY, _('Sticky weather'))
    )
    flight_climate = models.CharField(
        blank=True,
        null=True,
        max_length=1,
        choices=FLIGHT_CLIMATE_CHOICES,
        verbose_name=_('Flight climate')
    )

    @property
    def flight_months_str(self):
        """Returns the nuptial flight months as a string."""
        if self.flight_months.exists() is False:
            return DEFAULT_NONE_STR
        else:
            return ', '.join(str(month) for month in self.flight_months.all())

    LEAVES = 'LEAVES'
    LEAVES_TEXT = _('Leaves, grass and other vegetables')
    OMNIVOROUS = 'OMNIVOROUS'
    OMNIVOROUS_TEXT = _('Omnivorous (sugar water, honey, insects, meat, seeds, \
        nuts etc.)')
    SEEDS = 'SEEDS'
    SEEDS_TEXT = _('Mainly seeds and nuts but dead insects and sugar water, \
        honey too.')
    SUGAR_INSECTS = 'SUGAR_INSECTS'
    SUGAR_INSECTS_TEXT = _('Insects, meat, sugar water, honey etc.')

    NUTRITION_CHOICES = (
        (LEAVES, LEAVES_TEXT),
        (OMNIVOROUS, OMNIVOROUS_TEXT),
        (SEEDS, SEEDS_TEXT),
        (SUGAR_INSECTS, SUGAR_INSECTS_TEXT)
    )

    nutrition = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        choices=NUTRITION_CHOICES,
        verbose_name=_('Nutrition')
    )

    LONG_HIBERNATION = 'LONG'
    LONG_HIBERNATION_TEXT = _('yes: end of september until end of march')
    SHORT_HIBERNATION = 'SHORT'
    SHORT_HIBERNATION_TEXT = _('yes: end of november until end of'
                               ' february')
    NO_HIBERNATION = 'NO'
    NO_HIBERNATION_TEXT = _('No')

    HIBERNATION_CHOICES = (
        (NO_HIBERNATION, NO_HIBERNATION_TEXT),
        (LONG_HIBERNATION, LONG_HIBERNATION_TEXT),
        (SHORT_HIBERNATION, SHORT_HIBERNATION_TEXT)
    )

    hibernation = models.CharField(
        max_length=5,
        blank=True,
        null=True,
        choices=HIBERNATION_CHOICES,
        verbose_name=_('Hibernation required')
    )

    information_complete = models.BooleanField(
        default=False,
        verbose_name=_('Information complete')
    )

    nest_temperature = psql_fields.IntegerRangeField(
        blank=True,
        null=True,
        validators=[psql_validators.RangeMinValueValidator(0),
                    psql_validators.RangeMaxValueValidator(41)],
        verbose_name=_('Nest temperature (℃)'),
        help_text=INT_RANGE_HELP_TEXT
    )

    nest_humidity = psql_fields.IntegerRangeField(
        blank=True,
        null=True,
        validators=[psql_validators.RangeMinValueValidator(0),
                    psql_validators.RangeMaxValueValidator(100)],
        verbose_name=_('Nest relative humidity (%)'),
        help_text=INT_RANGE_HELP_TEXT
    )

    outworld_temperature = psql_fields.IntegerRangeField(
        blank=True,
        null=True,
        validators=[psql_validators.RangeMinValueValidator(0),
                    psql_validators.RangeMaxValueValidator(41)],
        verbose_name=_('Outworld temperature (℃)'),
        help_text=INT_RANGE_HELP_TEXT
    )

    outworld_humidity = psql_fields.IntegerRangeField(
        blank=True,
        null=True,
        validators=[psql_validators.RangeMinValueValidator(0),
                    psql_validators.RangeMaxValueValidator(100)],
        verbose_name=_('Outworld relative humidty (%)'),
        help_text=INT_RANGE_HELP_TEXT
    )

    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='created_ant_species',
        null=True, blank=True, on_delete=models.SET_NULL)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='updated_ant_species',
        null=True, blank=True, on_delete=models.SET_NULL)

    @property
    def main_image(self):
        return self.images.filter(main_image=True).first()

    def get_absolute_url(self):
        """Return the url to detail page."""
        return reverse('ant_detail', args=[self.slug])

    objects = AntSpeciesManager()

    class Meta(SpeciesMeta):
        pass


class AntSpeciesDistribution(AntSpecies):
    class Meta(SpeciesMeta):
        verbose_name = _('Species distribution')
        verbose_name_plural = _('Species distributions')
        proxy = True


class CommonName(models.Model):
    """
        Model for a common name of a species in a aspecific
        language.
    """
    name = models.CharField(max_length=200)
    language = models.CharField(max_length=7, choices=LANG_CHOICES)
    species = models.ForeignKey(Species, on_delete=models.CASCADE)

    class Meta:
        verbose_name = _('Common name')
        verbose_name_plural = _('Common names')
        ordering = ['name']

    def __str__(self):
        return '%s (%s)' % (self.name, dict(LANG_CHOICES)[self.language])


class InvalidName(models.Model):
    """Model for an invalid name of a species."""
    name = models.CharField(max_length=200)
    species = models.ForeignKey(Species,
                                related_name='invalid_names',
                                on_delete=models.CASCADE)

    class Meta:
        verbose_name = _('Invalid name')
        verbose_name_plural = _('Invalid names')
        ordering = ['name']

    def __str__(self):
        return self.name


class Image(models.Model):
    """Abstract model for an image."""
    image_file = ImageField(
        'Image file',
        upload_to='images'
    )
    caption = models.TextField(
        blank=True,
    )
    alt = models.TextField(
        'Alternative text',
        blank=True
    )
    source_url = models.URLField(
        'Image source',
        blank=True
    )
    source_caption = models.CharField(
        'Source caption',
        max_length=200,
        blank=True
    )
    main_image = models.BooleanField(
        'Main image',
        default=False
    )

    class Meta:
        abstract = True


class AntSpeciesImage(Image):
    """Model for an image of an ant species."""
    ant_species = models.ForeignKey(
        AntSpecies,
        models.CASCADE,
        related_name='images'
    )

    class Meta:
        verbose_name = _('Ant species image')
        verbose_name_plural = _('Ant species images')
