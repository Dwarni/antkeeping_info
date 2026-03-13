from django.test import TestCase
from django.urls import reverse
from psycopg2.extras import NumericRange
from rest_framework import status
from rest_framework.test import APIClient

from ants.models import (
    AntRegion,
    AntSize,
    AntSpecies,
    Distribution,
    Genus,
    Month,
    SubFamily,
    Tribe,
)


class APIViewsTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.sub_family = SubFamily.objects.create(name="Formicinae")
        self.tribe = Tribe.objects.create(name="Lasiini", sub_family=self.sub_family)
        self.genus = Genus.objects.create(name="Lasius", tribe=self.tribe)
        self.ant_species = AntSpecies.objects.create(
            name="Lasius niger", valid=True, genus=self.genus, slug="lasius-niger"
        )
        self.region = AntRegion.objects.create(
            name="Germany", code="DE", type="Country"
        )
        Distribution.objects.create(species=self.ant_species, region=self.region)

    def test_ant_species_list(self):
        response = self.client.get(reverse("api_ant_species"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], "Lasius niger")

    def test_ant_species_detail_by_id(self):
        response = self.client.get(
            reverse("api_ant_species_detail", args=[self.ant_species.id])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Lasius niger")

    def test_ant_species_detail_by_slug(self):
        response = self.client.get(
            reverse("api_ant_species_detail", args=["lasius-niger"])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Lasius niger")

    def test_ant_species_detail_by_name(self):
        response = self.client.get(
            reverse("api_ant_species_detail", args=["Lasius niger"])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Lasius niger")

    def test_ant_species_detail_not_found(self):
        response = self.client.get(
            reverse("api_ant_species_detail", args=["nonexistent-species"])
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_ant_species_detail_response_fields(self):
        """
        Verify the structure of the detail response. This test catches:
        - Serializer field misconfigurations (e.g. source='tribe.sub_family')
        - Missing nested relations (catches N+1 prefetch bugs via 500 errors)
        - 500 errors from broken IntegerRangeField source declarations
        Note: common_names and invalid_names use FKs to the parent Species
        model and are checked for presence only (not count) due to Django
        multi-table inheritance behaviour in TestCase transactions.
        """
        AntSize.objects.create(
            ant_species=self.ant_species, type=AntSize.WORKER, minimum=2.0, maximum=4.0
        )

        response = self.client.get(
            reverse("api_ant_species_detail", args=[self.ant_species.id])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertIn("genus", data)
        self.assertEqual(data["genus"]["name"], "Lasius")
        # Verifies GenusSerializer.sub_family uses source='tribe.sub_family'
        self.assertEqual(data["genus"]["sub_family"]["name"], "Formicinae")
        self.assertIn("distribution", data)
        self.assertEqual(len(data["distribution"]), 1)
        self.assertIn("common_names", data)
        self.assertIn("invalid_names", data)
        self.assertIn("sizes", data)
        self.assertEqual(len(data["sizes"]), 1)

    def test_genera_list(self):
        response = self.client.get(reverse("api_genera"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_ants_by_genus(self):
        response = self.client.get(reverse("api_ants_by_genus", args=[self.genus.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], "Lasius niger")

    def test_region_list(self):
        response = self.client.get(reverse("api_regions"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_region_detail_by_id(self):
        response = self.client.get(reverse("api_region", args=[self.region.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Germany")

    def test_region_detail_by_code(self):
        response = self.client.get(reverse("api_region", args=["DE"]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Germany")

    def test_ants_by_region_by_id(self):
        response = self.client.get(reverse("api_ants_by_region", args=[self.region.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_ants_by_region_by_code(self):
        response = self.client.get(reverse("api_ants_by_region", args=["DE"]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], "Lasius niger")

    def test_ants_by_region_not_found(self):
        response = self.client.get(reverse("api_ants_by_region", args=["nonexistent"]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_ants_by_region_diff(self):
        other_region = AntRegion.objects.create(
            name="France", code="FR", type="Country"
        )
        other_species = AntSpecies.objects.create(
            name="Lasius flavus", valid=True, genus=self.genus
        )
        Distribution.objects.create(species=other_species, region=other_region)

        response = self.client.get(
            reverse("api_ants_by_region_diff", args=["DE", "FR"])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [item["name"] for item in response.data]
        self.assertIn("Lasius niger", names)
        self.assertNotIn("Lasius flavus", names)

    def test_ant_species_detail_with_range_fields(self):
        """Species with IntegerRangeField values must return 200, not 500."""
        species_with_ranges = AntSpecies.objects.create(
            name="Lasius flavus",
            valid=True,
            genus=self.genus,
            flight_hour_range=NumericRange(8, 18),
            nest_temperature=NumericRange(20, 28),
            nest_humidity=NumericRange(40, 60),
            outworld_temperature=NumericRange(18, 30),
            outworld_humidity=NumericRange(30, 50),
        )
        response = self.client.get(
            reverse("api_ant_species_detail", args=[species_with_ranges.id])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.data["flight_hour_range"])
        self.assertIsNotNone(response.data["nest_temperature"])

    def test_ant_species_detail_range_fields_null(self):
        """Species without range data must serialize range fields as null without 500."""
        response = self.client.get(
            reverse("api_ant_species_detail", args=[self.ant_species.id])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data["flight_hour_range"])
        self.assertIsNone(response.data["nest_temperature"])

    def test_ant_species_detail_by_slug_with_range_fields(self):
        """Slug lookup for a species with range data must also return 200."""
        species_with_ranges = AntSpecies.objects.create(
            name="Lasius flavus",
            valid=True,
            genus=self.genus,
            slug="lasius-flavus",
            flight_hour_range=NumericRange(8, 18),
        )
        response = self.client.get(
            reverse("api_ant_species_detail", args=["lasius-flavus"])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], species_with_ranges.name)

    def test_ants_by_region_common(self):
        other_region = AntRegion.objects.create(
            name="France", code="FR", type="Country"
        )
        Distribution.objects.create(species=self.ant_species, region=other_region)

        response = self.client.get(
            reverse("api_ants_by_region_common", args=["DE", "FR"])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [item["name"] for item in response.data]
        self.assertIn("Lasius niger", names)


class NuptialFlightMonthsTest(TestCase):
    """Tests for NuptialFlightMonths endpoint.

    These tests verify that the serializer (including IntegerRangeField)
    works correctly end-to-end and would catch field misconfiguration bugs.
    """

    def setUp(self):
        self.client = APIClient()
        self.genus = Genus.objects.create(name="Lasius")
        self.ant_species = AntSpecies.objects.create(
            name="Lasius niger", valid=True, genus=self.genus
        )
        self.month = Month.objects.create(name="June")
        self.ant_species.flight_months.add(self.month)

    def test_nuptial_flight_months_status(self):
        response = self.client.get(reverse("api_ants_nuptial_flight_month"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_nuptial_flight_months_contains_species(self):
        response = self.client.get(reverse("api_ants_nuptial_flight_month"))
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], "Lasius niger")

    def test_nuptial_flight_months_response_fields(self):
        """Catches broken serializer field declarations (e.g. source=field_name)."""
        response = self.client.get(reverse("api_ants_nuptial_flight_month"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data[0]
        self.assertIn("id", data)
        self.assertIn("name", data)
        self.assertIn("flight_months", data)
        self.assertIn("flight_hour_range", data)
        self.assertIn("forbidden_in_eu", data)

    def test_nuptial_flight_months_name_filter(self):
        response = self.client.get(
            reverse("api_ants_nuptial_flight_month") + "?name=niger"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_nuptial_flight_months_name_filter_no_match(self):
        response = self.client.get(
            reverse("api_ants_nuptial_flight_month") + "?name=xyz"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_species_without_flight_months_excluded(self):
        AntSpecies.objects.create(name="Lasius flavus", valid=True, genus=self.genus)
        response = self.client.get(reverse("api_ants_nuptial_flight_month"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)


class APIv2ViewsTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.region = AntRegion.objects.create(name="Germany", code="DE")
        self.genus = Genus.objects.create(name="Lasius")
        self.ant_species = AntSpecies.objects.create(
            name="Lasius niger", valid=True, genus=self.genus, slug="lasius-niger"
        )
        for i in range(60):
            AntSpecies.objects.create(name=f"Species {i}", valid=True, genus=self.genus)

        Distribution.objects.create(species=self.ant_species, region=self.region)

    def test_v2_experimental_warning_header(self):
        """All V2 endpoints must carry the experimental Warning header."""
        endpoints = [
            reverse("v2_api_ant_species"),
            reverse("v2_api_regions"),
            reverse("v2_api_ant_species_detail", args=[self.ant_species.id]),
        ]
        for url in endpoints:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertIn("Warning", response.headers)
                self.assertIn("experimental", response.headers["Warning"])

    def test_v2_ant_species_list_paginated(self):
        response = self.client.get(reverse("v2_api_ant_species"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("count", response.data)
        self.assertIn("next", response.data)
        self.assertIn("previous", response.data)
        self.assertEqual(response.data["count"], 61)
        self.assertEqual(len(response.data["results"]), 50)

    def test_v2_region_list_paginated(self):
        response = self.client.get(reverse("v2_api_regions"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("count", response.data)
        self.assertEqual(response.data["count"], 1)

    def test_v2_ant_species_detail(self):
        response = self.client.get(
            reverse("v2_api_ant_species_detail", args=[self.ant_species.id])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Lasius niger")

    def test_v2_ant_species_list_forbidden_in_eu_filter(self):
        forbidden_species = AntSpecies.objects.create(
            name="Wasmannia auropunctata",
            valid=True,
            genus=self.genus,
            forbidden_in_eu=True,
        )
        response = self.client.get(
            reverse("v2_api_ant_species") + "?forbidden_in_eu=true"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["name"], forbidden_species.name)

    def test_v2_ant_species_list_forbidden_in_eu_filter_false(self):
        AntSpecies.objects.create(
            name="Wasmannia auropunctata",
            valid=True,
            genus=self.genus,
            forbidden_in_eu=True,
        )
        response = self.client.get(
            reverse("v2_api_ant_species") + "?forbidden_in_eu=false"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # 1 from setUp + 60 generic species, none forbidden
        self.assertEqual(response.data["count"], 61)

    def test_v2_ant_species_detail_by_slug(self):
        response = self.client.get(
            reverse("v2_api_ant_species_detail", args=["lasius-niger"])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Lasius niger")

    def test_v2_ant_species_detail_by_name(self):
        response = self.client.get(
            reverse("v2_api_ant_species_detail", args=["Lasius niger"])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Lasius niger")

    def test_v2_ant_species_detail_not_found(self):
        response = self.client.get(
            reverse("v2_api_ant_species_detail", args=["nonexistent-species"])
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_v2_ant_species_detail_with_range_fields(self):
        """Species with IntegerRangeField values must return 200, not 500."""
        species_with_ranges = AntSpecies.objects.create(
            name="Lasius flavus",
            valid=True,
            genus=self.genus,
            slug="lasius-flavus",
            flight_hour_range=NumericRange(8, 18),
            nest_temperature=NumericRange(20, 28),
        )
        response = self.client.get(
            reverse("v2_api_ant_species_detail", args=[species_with_ranges.id])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.data["flight_hour_range"])

    def test_v2_ant_species_search_filter(self):
        response = self.client.get(reverse("v2_api_ant_species") + "?search=niger")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["name"], "Lasius niger")

    def test_v2_ant_species_search_filter_case_insensitive(self):
        response = self.client.get(reverse("v2_api_ant_species") + "?search=NIGER")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_v2_ant_species_search_filter_no_match(self):
        response = self.client.get(
            reverse("v2_api_ant_species") + "?search=xxxxxxnotfound"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)

    def test_v2_ant_species_region_filter_by_code(self):
        response = self.client.get(reverse("v2_api_ant_species") + "?region=DE")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["name"], "Lasius niger")

    def test_v2_ant_species_region_filter_by_id(self):
        response = self.client.get(
            reverse("v2_api_ant_species") + f"?region={self.region.id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_v2_ant_species_region_filter_no_match(self):
        response = self.client.get(reverse("v2_api_ant_species") + "?region=XX")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)

    def test_v2_ant_species_page_size(self):
        response = self.client.get(reverse("v2_api_ant_species") + "?page_size=10")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 10)
        self.assertEqual(response.data["count"], 61)
        self.assertIsNotNone(response.data["next"])


class V2NuptialFlightMonthsTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.genus = Genus.objects.create(name="Lasius")
        self.july = Month.objects.create(name="July")
        self.august = Month.objects.create(name="August")
        self.ant_july = AntSpecies.objects.create(
            name="Lasius niger", valid=True, genus=self.genus
        )
        self.ant_july.flight_months.add(self.july)
        self.ant_august = AntSpecies.objects.create(
            name="Lasius flavus", valid=True, genus=self.genus
        )
        self.ant_august.flight_months.add(self.august)

    def test_v2_nuptial_flight_months_status(self):
        response = self.client.get(reverse("v2_api_ants_nuptial_flight_month"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_v2_nuptial_flight_months_paginated(self):
        response = self.client.get(reverse("v2_api_ants_nuptial_flight_month"))
        self.assertIn("count", response.data)
        self.assertIn("results", response.data)
        self.assertEqual(response.data["count"], 2)

    def test_v2_nuptial_flight_months_experimental_warning(self):
        response = self.client.get(reverse("v2_api_ants_nuptial_flight_month"))
        self.assertIn("Warning", response.headers)
        self.assertIn("experimental", response.headers["Warning"])

    def test_v2_nuptial_flight_months_month_filter(self):
        response = self.client.get(
            reverse("v2_api_ants_nuptial_flight_month") + f"?month={self.july.id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["name"], "Lasius niger")

    def test_v2_nuptial_flight_months_month_filter_no_match(self):
        other_month = Month.objects.create(name="January")
        response = self.client.get(
            reverse("v2_api_ants_nuptial_flight_month") + f"?month={other_month.id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)


class V2AntSizeViewsTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.region = AntRegion.objects.create(name="Germany", code="DE")
        self.genus_lasius = Genus.objects.create(name="Lasius")
        self.genus_formica = Genus.objects.create(name="Formica")

        self.lasius_niger = AntSpecies.objects.create(
            name="Lasius niger", valid=True, genus=self.genus_lasius
        )
        self.formica_rufa = AntSpecies.objects.create(
            name="Formica rufa", valid=True, genus=self.genus_formica
        )
        Distribution.objects.create(species=self.lasius_niger, region=self.region)

        AntSize.objects.create(
            ant_species=self.lasius_niger, type="WORKER", minimum=2.0, maximum=4.0
        )
        AntSize.objects.create(
            ant_species=self.lasius_niger, type="QUEEN", minimum=8.0, maximum=10.0
        )
        AntSize.objects.create(
            ant_species=self.formica_rufa, type="WORKER", minimum=5.0, maximum=8.0
        )
        AntSize.objects.create(
            ant_species=self.formica_rufa, type="QUEEN", minimum=9.0, maximum=12.0
        )

    # --- Experimental warning header ---

    def test_worker_sizes_experimental_warning_header(self):
        response = self.client.get(reverse("v2_api_ant_worker_sizes"))
        self.assertIn("Warning", response.headers)
        self.assertIn("experimental", response.headers["Warning"])

    def test_queen_sizes_experimental_warning_header(self):
        response = self.client.get(reverse("v2_api_ant_queen_sizes"))
        self.assertIn("Warning", response.headers)
        self.assertIn("experimental", response.headers["Warning"])

    # --- Pagination ---

    def test_worker_sizes_paginated(self):
        response = self.client.get(reverse("v2_api_ant_worker_sizes"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("count", response.data)
        self.assertIn("results", response.data)
        self.assertEqual(response.data["count"], 2)

    def test_queen_sizes_paginated(self):
        response = self.client.get(reverse("v2_api_ant_queen_sizes"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)

    # --- Response fields ---

    def test_worker_sizes_response_fields(self):
        response = self.client.get(reverse("v2_api_ant_worker_sizes"))
        result = response.data["results"][0]
        self.assertIn("id", result)
        self.assertIn("name", result)
        self.assertIn("minimum", result)
        self.assertIn("maximum", result)

    # --- Region filter ---

    def test_worker_sizes_filter_by_region_code(self):
        response = self.client.get(reverse("v2_api_ant_worker_sizes") + "?region=DE")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["name"], "Lasius niger")

    def test_worker_sizes_filter_by_region_code_case_insensitive(self):
        response = self.client.get(reverse("v2_api_ant_worker_sizes") + "?region=de")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_worker_sizes_filter_by_region_id(self):
        response = self.client.get(
            reverse("v2_api_ant_worker_sizes") + f"?region={self.region.id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_worker_sizes_filter_by_region_no_match(self):
        response = self.client.get(reverse("v2_api_ant_worker_sizes") + "?region=XX")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)

    # --- Genus filter ---

    def test_worker_sizes_filter_by_genus_name(self):
        response = self.client.get(
            reverse("v2_api_ant_worker_sizes") + "?genus=Lasius"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["name"], "Lasius niger")

    def test_worker_sizes_filter_by_genus_name_case_insensitive(self):
        response = self.client.get(
            reverse("v2_api_ant_worker_sizes") + "?genus=lasius"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_worker_sizes_filter_by_genus_id(self):
        response = self.client.get(
            reverse("v2_api_ant_worker_sizes") + f"?genus={self.genus_lasius.id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_worker_sizes_filter_by_genus_no_match(self):
        response = self.client.get(
            reverse("v2_api_ant_worker_sizes") + "?genus=Nonexistent"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)

    # --- Queen size filters (smoke tests) ---

    def test_queen_sizes_filter_by_region(self):
        response = self.client.get(reverse("v2_api_ant_queen_sizes") + "?region=DE")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_queen_sizes_filter_by_genus(self):
        response = self.client.get(
            reverse("v2_api_ant_queen_sizes") + "?genus=Formica"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["name"], "Formica rufa")


class AntSpeciesFilterTest(TestCase):
    """Tests for the new filter parameters on /api/v2/ants/."""

    def setUp(self):
        self.client = APIClient()
        self.genus_lasius = Genus.objects.create(name="Lasius")
        self.genus_formica = Genus.objects.create(name="Formica")

        self.lasius_niger = AntSpecies.objects.create(
            name="Lasius niger",
            valid=True,
            genus=self.genus_lasius,
            slug="lasius-niger",
            hibernation="LONG",
            worker_polymorphism=False,
            nutrition="SUGAR_INSECTS",
            colony_structure="MONO",
            founding="c",
        )
        self.formica_rufa = AntSpecies.objects.create(
            name="Formica rufa",
            valid=True,
            genus=self.genus_formica,
            slug="formica-rufa",
            hibernation="SHORT",
            worker_polymorphism=True,
            nutrition="OMNIVOROUS",
            colony_structure="POLY",
            founding="sc",
        )
        self.invalid_species = AntSpecies.objects.create(
            name="Lasius obsoletus",
            valid=False,
            genus=self.genus_lasius,
            slug="lasius-obsoletus",
        )
        # Worker sizes for Lasius niger: 2–4 mm
        AntSize.objects.create(
            ant_species=self.lasius_niger,
            type=AntSize.WORKER,
            minimum=2,
            maximum=4,
        )
        # Worker sizes for Formica rufa: 5–9 mm
        AntSize.objects.create(
            ant_species=self.formica_rufa,
            type=AntSize.WORKER,
            minimum=5,
            maximum=9,
        )

    def _get(self, params):
        return self.client.get(reverse("v2_api_ant_species") + "?" + params)

    # --- valid filter ---

    def test_valid_defaults_to_true(self):
        response = self._get("")
        names = [r["name"] for r in response.data["results"]]
        self.assertIn("Lasius niger", names)
        self.assertIn("Formica rufa", names)
        self.assertNotIn("Lasius obsoletus", names)

    def test_valid_false_returns_invalid_species(self):
        response = self._get("valid=false")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [r["name"] for r in response.data["results"]]
        self.assertIn("Lasius obsoletus", names)
        self.assertNotIn("Lasius niger", names)

    # --- genus filter ---

    def test_filter_by_genus_slug(self):
        response = self._get("genus=lasius")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["name"], "Lasius niger")

    def test_filter_by_genus_name(self):
        response = self._get("genus=Lasius")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["name"], "Lasius niger")

    def test_filter_by_genus_id(self):
        response = self._get(f"genus={self.genus_lasius.pk}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["name"], "Lasius niger")

    # --- hibernation filter ---

    def test_filter_by_hibernation(self):
        response = self._get("hibernation=LONG")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["name"], "Lasius niger")

    # --- worker_polymorphism filter ---

    def test_filter_by_worker_polymorphism_true(self):
        response = self._get("worker_polymorphism=true")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["name"], "Formica rufa")

    def test_filter_by_worker_polymorphism_false(self):
        response = self._get("worker_polymorphism=false")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["name"], "Lasius niger")

    # --- nutrition filter ---

    def test_filter_by_nutrition(self):
        response = self._get("nutrition=OMNIVOROUS")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["name"], "Formica rufa")

    # --- colony_structure filter ---

    def test_filter_by_colony_structure(self):
        response = self._get("colony_structure=MONO")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["name"], "Lasius niger")

    # --- founding filter ---

    def test_filter_by_founding(self):
        response = self._get("founding=sc")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["name"], "Formica rufa")

    # --- size filters ---

    def test_filter_by_size_min_matches_overlapping_range(self):
        # size_min=3: Lasius niger (2–4) covers 3, Formica rufa (5–9) does not
        response = self._get("size_min=3")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["name"], "Lasius niger")

    def test_filter_by_size_max_matches_overlapping_range(self):
        # size_max=6: Formica rufa (5–9) covers 6, Lasius niger (2–4) does not
        response = self._get("size_max=6")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["name"], "Formica rufa")

    def test_filter_by_size_min_and_max_combined(self):
        # Both species have ranges that overlap [3, 6]? No:
        # Lasius niger 2–4 covers 3 but max=4 < 6, so size_max=6 filter fails for it.
        # Formica rufa 5–9 covers 6 but min=5 > 3, so size_min=3 filter fails for it.
        # Result: no species matches both constraints simultaneously.
        response = self._get("size_min=3&size_max=6")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)

    def test_filter_by_size_range_both_match(self):
        # size_min=5&size_max=8: Formica rufa (5–9) covers both 5 and 8
        response = self._get("size_min=5&size_max=8")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["name"], "Formica rufa")
