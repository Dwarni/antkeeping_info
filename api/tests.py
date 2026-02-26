from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from ants.models import AntSpecies, Genus, Tribe, SubFamily, AntRegion, \
    Distribution, Month, AntSize, CommonName, InvalidName


class APIViewsTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.sub_family = SubFamily.objects.create(name="Formicinae")
        self.tribe = Tribe.objects.create(name="Lasiini", sub_family=self.sub_family)
        self.genus = Genus.objects.create(name="Lasius", tribe=self.tribe)
        self.ant_species = AntSpecies.objects.create(
            name="Lasius niger", valid=True, genus=self.genus,
            slug="lasius-niger"
        )
        self.region = AntRegion.objects.create(name="Germany", code="DE", type="Country")
        Distribution.objects.create(species=self.ant_species, region=self.region)

    def test_ant_species_list(self):
        response = self.client.get(reverse('api_ant_species'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], "Lasius niger")

    def test_ant_species_detail_by_id(self):
        response = self.client.get(
            reverse('api_ant_species_detail', args=[self.ant_species.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], "Lasius niger")

    def test_ant_species_detail_by_slug(self):
        response = self.client.get(
            reverse('api_ant_species_detail', args=["lasius-niger"]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], "Lasius niger")

    def test_ant_species_detail_by_name(self):
        response = self.client.get(
            reverse('api_ant_species_detail', args=["Lasius niger"]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], "Lasius niger")

    def test_ant_species_detail_not_found(self):
        response = self.client.get(
            reverse('api_ant_species_detail', args=["nonexistent-species"]))
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
            ant_species=self.ant_species, type=AntSize.WORKER,
            minimum=2.0, maximum=4.0)

        response = self.client.get(
            reverse('api_ant_species_detail', args=[self.ant_species.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertIn('genus', data)
        self.assertEqual(data['genus']['name'], 'Lasius')
        # Verifies GenusSerializer.sub_family uses source='tribe.sub_family'
        self.assertEqual(data['genus']['sub_family']['name'], 'Formicinae')
        self.assertIn('distribution', data)
        self.assertEqual(len(data['distribution']), 1)
        self.assertIn('common_names', data)
        self.assertIn('invalid_names', data)
        self.assertIn('sizes', data)
        self.assertEqual(len(data['sizes']), 1)

    def test_genera_list(self):
        response = self.client.get(reverse('api_genera'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_ants_by_genus(self):
        response = self.client.get(
            reverse('api_ants_by_genus', args=[self.genus.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], "Lasius niger")

    def test_region_list(self):
        response = self.client.get(reverse('api_regions'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_region_detail_by_id(self):
        response = self.client.get(
            reverse('api_region', args=[self.region.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], "Germany")

    def test_region_detail_by_code(self):
        response = self.client.get(reverse('api_region', args=["DE"]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], "Germany")

    def test_ants_by_region_by_id(self):
        response = self.client.get(
            reverse('api_ants_by_region', args=[self.region.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_ants_by_region_by_code(self):
        response = self.client.get(reverse('api_ants_by_region', args=["DE"]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], "Lasius niger")

    def test_ants_by_region_not_found(self):
        response = self.client.get(
            reverse('api_ants_by_region', args=["nonexistent"]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_ants_by_region_diff(self):
        other_region = AntRegion.objects.create(name="France", code="FR", type="Country")
        other_species = AntSpecies.objects.create(
            name="Lasius flavus", valid=True, genus=self.genus)
        Distribution.objects.create(species=other_species, region=other_region)

        response = self.client.get(
            reverse('api_ants_by_region_diff', args=["DE", "FR"]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [item['name'] for item in response.data]
        self.assertIn("Lasius niger", names)
        self.assertNotIn("Lasius flavus", names)

    def test_ants_by_region_common(self):
        other_region = AntRegion.objects.create(name="France", code="FR", type="Country")
        Distribution.objects.create(species=self.ant_species, region=other_region)

        response = self.client.get(
            reverse('api_ants_by_region_common', args=["DE", "FR"]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [item['name'] for item in response.data]
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
            name="Lasius niger", valid=True, genus=self.genus)
        self.month = Month.objects.create(name="June")
        self.ant_species.flight_months.add(self.month)

    def test_nuptial_flight_months_status(self):
        response = self.client.get(reverse('api_ants_nuptial_flight_month'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_nuptial_flight_months_contains_species(self):
        response = self.client.get(reverse('api_ants_nuptial_flight_month'))
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], "Lasius niger")

    def test_nuptial_flight_months_response_fields(self):
        """Catches broken serializer field declarations (e.g. source=field_name)."""
        response = self.client.get(reverse('api_ants_nuptial_flight_month'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data[0]
        self.assertIn('id', data)
        self.assertIn('name', data)
        self.assertIn('flight_months', data)
        self.assertIn('flight_hour_range', data)

    def test_nuptial_flight_months_name_filter(self):
        response = self.client.get(
            reverse('api_ants_nuptial_flight_month') + '?name=niger')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_nuptial_flight_months_name_filter_no_match(self):
        response = self.client.get(
            reverse('api_ants_nuptial_flight_month') + '?name=xyz')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_species_without_flight_months_excluded(self):
        AntSpecies.objects.create(
            name="Lasius flavus", valid=True, genus=self.genus)
        response = self.client.get(reverse('api_ants_nuptial_flight_month'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)


class APIv2ViewsTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.region = AntRegion.objects.create(name="Germany", code="DE")
        self.genus = Genus.objects.create(name="Lasius")
        self.ant_species = AntSpecies.objects.create(
            name="Lasius niger", valid=True, genus=self.genus
        )
        for i in range(60):
            AntSpecies.objects.create(name=f"Species {i}", valid=True, genus=self.genus)

        Distribution.objects.create(species=self.ant_species, region=self.region)

    def test_v2_experimental_warning_header(self):
        """All V2 endpoints must carry the experimental Warning header."""
        endpoints = [
            reverse('v2_api_ant_species'),
            reverse('v2_api_regions'),
            reverse('v2_api_ant_species_detail', args=[self.ant_species.id]),
        ]
        for url in endpoints:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertIn('Warning', response.headers)
                self.assertIn('experimental', response.headers['Warning'])

    def test_v2_ant_species_list_paginated(self):
        response = self.client.get(reverse('v2_api_ant_species'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('count', response.data)
        self.assertIn('next', response.data)
        self.assertIn('previous', response.data)
        self.assertEqual(response.data['count'], 61)
        self.assertEqual(len(response.data['results']), 50)

    def test_v2_region_list_paginated(self):
        response = self.client.get(reverse('v2_api_regions'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('count', response.data)
        self.assertEqual(response.data['count'], 1)

    def test_v2_ant_species_detail(self):
        response = self.client.get(
            reverse('v2_api_ant_species_detail', args=[self.ant_species.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], "Lasius niger")
