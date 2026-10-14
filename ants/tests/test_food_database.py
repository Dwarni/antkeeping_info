from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from antkeeping_info.sitemaps import FoodItemSitemap
from ants.models import AntSpecies, FoodItem, Genus, SpeciesFoodRating


class FoodDatabaseViewsTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user1 = User.objects.create_user(username="keeper1", password="password123")
        cls.user2 = User.objects.create_user(username="keeper2", password="password123")

        cls.genus_lasius = Genus.objects.create(name="Lasius")
        cls.genus_camponotus = Genus.objects.create(name="Camponotus")

        cls.species_niger = AntSpecies.objects.create(
            name="Lasius niger", valid=True, genus=cls.genus_lasius, slug="lasius-niger"
        )
        cls.species_flavus = AntSpecies.objects.create(
            name="Lasius flavus", valid=True, genus=cls.genus_lasius, slug="lasius-flavus"
        )
        cls.species_herculeanus = AntSpecies.objects.create(
            name="Camponotus herculeanus", valid=True, genus=cls.genus_camponotus, slug="camponotus-herculeanus"
        )

        cls.food_insects = FoodItem.objects.create(
            name="Fruit Flies (Drosophila)",
            category=FoodItem.PROTEIN,
            description="Small, soft-bodied feeder flies ideal for founding and young colonies.",
        )
        cls.food_honey = FoodItem.objects.create(
            name="Wildflower Honey",
            category=FoodItem.SUGAR,
            description="Pure unprocessed raw flower honey.",
        )

        # Votes for Fruit Flies:
        # Lasius niger: 2 UP, 0 DOWN -> 100%
        SpeciesFoodRating.objects.create(
            species=cls.species_niger, food_item=cls.food_insects, user=cls.user1, vote=SpeciesFoodRating.UP
        )
        SpeciesFoodRating.objects.create(
            species=cls.species_niger, food_item=cls.food_insects, user=cls.user2, vote=SpeciesFoodRating.UP
        )
        # Camponotus herculeanus: 1 UP, 1 DOWN -> 50%
        SpeciesFoodRating.objects.create(
            species=cls.species_herculeanus, food_item=cls.food_insects, user=cls.user1, vote=SpeciesFoodRating.UP
        )
        SpeciesFoodRating.objects.create(
            species=cls.species_herculeanus, food_item=cls.food_insects, user=cls.user2, vote=SpeciesFoodRating.DOWN
        )

    def test_food_item_get_absolute_url(self):
        url = self.food_insects.get_absolute_url()
        self.assertEqual(url, reverse("food_item_detail", args=[self.food_insects.pk]))

    def test_food_overview_view_default(self):
        url = reverse("food_overview")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "ants/food_overview.html")
        self.assertTemplateUsed(response, "ants/food_overview_list.html")
        self.assertContains(response, "Ant Food Database")
        self.assertContains(response, "Fruit Flies (Drosophila)")
        self.assertIn("category_counts", response.context)
        self.assertEqual(response.context["category_counts"].get(FoodItem.PROTEIN), 1)
        self.assertEqual(response.context["category_counts"].get(FoodItem.SUGAR), 1)

    def test_food_overview_view_category_switch(self):
        url = reverse("food_overview")
        response = self.client.get(url, {"category": FoodItem.SUGAR})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["selected_category"], FoodItem.SUGAR)
        self.assertContains(response, "Wildflower Honey")
        # Fruit flies are PROTEIN, so should not be in SUGAR list
        self.assertNotContains(response, "Fruit Flies (Drosophila)")

    def test_food_overview_empty_category(self):
        url = reverse("food_overview")
        response = self.client.get(url, {"category": FoodItem.SEEDS})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No food items in this category yet")

    def test_food_overview_acceptance_metrics_computed(self):
        url = reverse("food_overview")
        response = self.client.get(url, {"category": FoodItem.PROTEIN})
        self.assertEqual(response.status_code, 200)
        food_data = response.context["food_data"]
        entry = next(e for e in food_data if e["food_item"] == self.food_insects)
        # Total votes: 3 up, 1 down = 4 total, net score 2, acceptance 75%
        self.assertEqual(entry["total_ratings"], 4)
        self.assertEqual(entry["overall_net_score"], 2)
        self.assertEqual(entry["acceptance_pct"], 75)
        self.assertContains(response, "75% acceptance")

    def test_food_item_detail_view(self):
        url = reverse("food_item_detail", args=[self.food_insects.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "ants/food_item_detail.html")
        self.assertContains(response, "Fruit Flies (Drosophila)")
        self.assertContains(response, "Feeding & Suitability Guide")
        self.assertContains(response, "Why ants need protein")
        self.assertContains(response, "Popularity by Ant Genus")

        context = response.context
        self.assertEqual(context["total_votes"], 4)
        self.assertEqual(context["total_up"], 3)
        self.assertEqual(context["total_down"], 1)
        self.assertEqual(context["overall_net"], 2)
        self.assertEqual(context["overall_acceptance"], 75)

        # Genus breakdown
        genus_list = context["genus_list"]
        genus_names = [g["genus"] for g in genus_list]
        self.assertIn("Lasius", genus_names)
        self.assertIn("Camponotus", genus_names)

        lasius_data = next(g for g in genus_list if g["genus"] == "Lasius")
        self.assertEqual(lasius_data["acceptance_pct"], 100)
        self.assertEqual(lasius_data["up_count"], 2)

        camponotus_data = next(g for g in genus_list if g["genus"] == "Camponotus")
        self.assertEqual(camponotus_data["acceptance_pct"], 50)

    def test_food_item_detail_404(self):
        url = reverse("food_item_detail", args=[999999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_food_item_sitemap(self):
        sitemap = FoodItemSitemap()
        items = list(sitemap.items())
        self.assertIn(self.food_insects, items)
        self.assertIn(self.food_honey, items)
        loc = sitemap.location(self.food_insects)
        self.assertEqual(loc, self.food_insects.get_absolute_url())

    def test_search_autocomplete_links_to_detail(self):
        url = reverse("search_autocomplete")
        response = self.client.get(url, {"q": "Fruit"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        food_suggestions = data.get("food", [])
        self.assertTrue(any(f["url"] == self.food_insects.get_absolute_url() for f in food_suggestions))
