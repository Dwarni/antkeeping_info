from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from ants.models import AntSpecies, Genus, AntRegion, Distribution

class APIViewsTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.region = AntRegion.objects.create(name="Germany", code="DE")
        self.genus = Genus.objects.create(name="Lasius")
        self.ant_species = AntSpecies.objects.create(
            name="Lasius niger", valid=True, genus=self.genus
        )
        Distribution.objects.create(species=self.ant_species, region=self.region)

    def test_ant_species_list(self):
        response = self.client.get(reverse('api_ant_species'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], "Lasius niger")

    def test_ant_species_detail(self):
        response = self.client.get(reverse('api_ant_species_detail', args=[self.ant_species.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], "Lasius niger")

    def test_genera_list(self):
        response = self.client.get(reverse('api_genera'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_region_list(self):
        response = self.client.get(reverse('api_regions'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        
    def test_ants_by_region(self):
        response = self.client.get(reverse('api_ants_by_region', args=[self.region.id]))
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
        
    def test_v2_ant_species_list_paginated(self):
        response = self.client.get(reverse('v2_api_ant_species'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should be paginated to 50 items
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
        response = self.client.get(reverse('v2_api_ant_species_detail', args=[self.ant_species.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], "Lasius niger")
