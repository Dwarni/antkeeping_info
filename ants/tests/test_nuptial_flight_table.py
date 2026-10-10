import datetime

from django.test import TestCase
from django.urls import reverse

from ants.models import AntRegion, AntSpecies, Distribution, Genus, Month


class NuptialFlightTableViewTest(TestCase):
    def setUp(self):
        self.genus = Genus.objects.create(name="Lasius")
        self.species = AntSpecies.objects.create(
            name="Lasius niger", valid=True, genus=self.genus, slug="lasius-niger"
        )
        self.month_may, _ = Month.objects.get_or_create(id=5, defaults={"name": "May"})
        self.current_month_num = datetime.date.today().month
        self.current_month_obj, _ = Month.objects.get_or_create(
            id=self.current_month_num,
            defaults={"name": "Current"},
        )
        self.species.flight_months.add(self.month_may, self.current_month_obj)
        self.region = AntRegion.objects.create(name="Germany", code="DE")
        Distribution.objects.create(species=self.species, region=self.region)

    def test_main_page_renders_successfully(self):
        url = reverse("nuptial_flight_table")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nuptial Flight Table")
        self.assertContains(response, "quick-current-month-btn")
        self.assertContains(response, "filter-card")

    def test_rows_fragment_renders_successfully(self):
        url = reverse("nuptial_flight_table_rows")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Lasius niger")
        self.assertContains(response, "flight-pill")
        self.assertContains(response, "nuptial-legend")
        self.assertContains(response, "sticky-col")
        self.assertEqual(response.context["current_month"], self.current_month_num)

    def test_rows_filter_by_current_month(self):
        url = reverse("nuptial_flight_table_rows") + "?month=current"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Lasius niger")

    def test_rows_filter_no_results_renders_empty_state(self):
        url = reverse("nuptial_flight_table_rows") + "?name=nonexistentspecies"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No matching ant species found")
