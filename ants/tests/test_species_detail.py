from decimal import Decimal
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from psycopg2.extras import NumericRange

from ants.models import (
    AntRegion,
    AntSize,
    AntSpecies,
    AntSpeciesImage,
    Distribution,
    Family,
    Genus,
    SubFamily,
    Tribe,
)
from ants.templatetags.ants import antmaps_species_url


class AntSpeciesDetailViewTest(TestCase):
    def setUp(self):
        self.family = Family.objects.create(name="Formicidae")
        self.subfamily = SubFamily.objects.create(name="Formicinae", family=self.family)
        self.tribe = Tribe.objects.create(name="Lasiini", sub_family=self.subfamily)
        self.genus = Genus.objects.create(name="Lasius", tribe=self.tribe)

        self.species = AntSpecies.objects.create(
            name="Lasius niger",
            valid=True,
            genus=self.genus,
            slug="lasius-niger",
            author="Linnaeus",
            year=1758,
            hibernation=AntSpecies.LONG_HIBERNATION,
            colony_structure=AntSpecies.MONOGYNOUS,
            founding=AntSpecies.CLAUSTRAL,
            nutrition=AntSpecies.SUGAR_INSECTS,
            nest_temperature=NumericRange(21, 29),
            nest_humidity=NumericRange(70, 91),
            outworld_temperature=NumericRange(18, 31),
            outworld_humidity=NumericRange(30, 71),
            worker_polymorphism=False,
            information_complete=True,
            forbidden_in_eu=False,
        )

        self.region = AntRegion.objects.create(
            name="Germany", code="DE", type="Country"
        )
        Distribution.objects.create(species=self.species, region=self.region)

        self.worker_size = AntSize.objects.create(
            ant_species=self.species,
            type=AntSize.WORKER,
            minimum=Decimal("3.00"),
            maximum=Decimal("5.00"),
        )
        self.queen_size = AntSize.objects.create(
            ant_species=self.species,
            type=AntSize.QUEEN,
            minimum=Decimal("8.00"),
            maximum=Decimal("9.00"),
        )

        self.url = reverse("ant_detail", args=[self.species.slug])

    def test_detail_view_status_and_template(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "ants/antspecies_detail/antspecies_detail.html"
        )
        self.assertTemplateUsed(
            response, "ants/antspecies_detail/antspecies_detail_quick_parameters.html"
        )
        self.assertTemplateUsed(
            response, "ants/antspecies_detail/antspecies_detail_keeping_parameters.html"
        )
        self.assertTemplateUsed(
            response, "ants/antspecies_detail/antspecies_detail_sizes.html"
        )
        self.assertTemplateUsed(
            response, "ants/antspecies_detail/antspecies_detail_distribution.html"
        )

    def test_quick_parameters_content(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "species-quick-params")
        self.assertContains(response, "Nest Temp.")
        self.assertContains(response, "21 ℃ - 28 ℃")
        self.assertContains(response, "Nest Moisture")
        self.assertContains(response, "70 % - 90 %")
        self.assertContains(response, "Outworld Temp.")
        self.assertContains(response, "18 ℃ - 30 ℃")
        self.assertContains(response, "Hibernation")
        self.assertContains(response, "Long")
        self.assertContains(response, "Claustral")
        self.assertContains(response, "Monogynous")

    def test_placeholder_rendered_when_no_image(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "species-placeholder-card")
        self.assertContains(response, "No photos for this species yet")

    def test_gallery_rendered_when_multiple_images(self):
        dummy_image = SimpleUploadedFile(
            name="test.jpg",
            content=b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b",
            content_type="image/jpeg",
        )
        AntSpeciesImage.objects.create(
            ant_species=self.species,
            image_file=dummy_image,
            caption="Queen dorsal view",
            main_image=True,
        )
        AntSpeciesImage.objects.create(
            ant_species=self.species,
            image_file=dummy_image,
            caption="Worker lateral view",
            main_image=False,
        )
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "species-gallery-thumbs")
        self.assertContains(response, "species-gallery-thumb")

    def test_forbidden_in_eu_warning(self):
        self.species.forbidden_in_eu = True
        self.species.save()
        response = self.client.get(self.url)
        self.assertContains(response, "Invasive Alien Species Warning (EU)")
        self.assertContains(response, "alert-danger")

    def test_incomplete_information_alert(self):
        self.species.information_complete = False
        self.species.save()
        response = self.client.get(self.url)
        self.assertContains(response, "Species information is not complete yet!")

    def test_antmaps_url_filter(self):
        self.assertEqual(
            antmaps_species_url("Lasius niger"),
            "https://antmaps.org/?mode=species&species=Lasius.niger",
        )
        self.assertEqual(
            antmaps_species_url("Camponotus ligniperda"),
            "https://antmaps.org/?mode=species&species=Camponotus.ligniperda",
        )
        self.assertEqual(antmaps_species_url(""), "https://antmaps.org/")

    def test_distribution_tags_and_filter_search(self):
        response = self.client.get(self.url)
        self.assertContains(response, "country-tag")
        self.assertContains(response, "Germany")
        self.assertContains(response, "antmaps.org")

    def test_sizes_visualizer_has_dark_mode_filter(self):
        response = self.client.get(self.url)
        self.assertContains(response, "ant-size-card")
        self.assertContains(response, "ant-size-box")
        self.assertContains(response, "3.00")
