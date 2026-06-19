from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from ants.models import FoodItem


def _make_food(name="Mealworms", category=FoodItem.PROTEIN):
    return FoodItem.objects.create(name=name, category=category)


class FoodOverviewCreateItemViewTest(TestCase):
    def setUp(self):
        self.url = reverse("food_overview_new_item")
        self.user = User.objects.create_user(username="tester", password="pass")

    def test_anonymous_redirects_to_login(self):
        response = self.client.post(self.url, {"name": "Honey water", "category": FoodItem.SUGAR})
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/", response["Location"])
        self.assertFalse(FoodItem.objects.filter(name="Honey water").exists())

    def test_logged_in_creates_item_and_sets_created_by(self):
        self.client.login(username="tester", password="pass")
        response = self.client.post(
            self.url, {"name": "Honey water", "category": FoodItem.SUGAR, "description": "Sugar water mix"}
        )
        self.assertEqual(response.status_code, 200)
        item = FoodItem.objects.get(name="Honey water")
        self.assertEqual(item.created_by, self.user)
        self.assertEqual(item.category, FoodItem.SUGAR)
        self.assertContains(response, "Honey water")

    def test_invalid_category_rejected(self):
        self.client.login(username="tester", password="pass")
        response = self.client.post(self.url, {"name": "Honey water", "category": "NOT_A_CATEGORY"})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(FoodItem.objects.filter(name="Honey water").exists())

    def test_exact_duplicate_name_is_clean_form_error(self):
        _make_food(name="Mealworms", category=FoodItem.PROTEIN)
        self.client.login(username="tester", password="pass")
        response = self.client.post(self.url, {"name": "Mealworms", "category": FoodItem.PROTEIN})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(FoodItem.objects.filter(name="Mealworms").count(), 1)

    def test_rate_limit_blocks_after_max_creations_in_window(self):
        from ants.views import FoodOverviewCreateItemView

        self.client.login(username="tester", password="pass")
        for i in range(FoodOverviewCreateItemView.MAX_CREATIONS_PER_WINDOW):
            response = self.client.post(self.url, {"name": f"Food {i}", "category": FoodItem.PROTEIN})
            self.assertEqual(response.status_code, 200)
        self.assertEqual(
            FoodItem.objects.filter(created_by=self.user).count(),
            FoodOverviewCreateItemView.MAX_CREATIONS_PER_WINDOW,
        )

        response = self.client.post(self.url, {"name": "One too many", "category": FoodItem.PROTEIN})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(FoodItem.objects.filter(name="One too many").exists())

    def test_rate_limit_does_not_count_other_users(self):
        from ants.views import FoodOverviewCreateItemView

        other = User.objects.create_user(username="other", password="pass")
        for i in range(FoodOverviewCreateItemView.MAX_CREATIONS_PER_WINDOW):
            _make_food(name=f"Other food {i}")
            FoodItem.objects.filter(name=f"Other food {i}").update(created_by=other)

        self.client.login(username="tester", password="pass")
        response = self.client.post(self.url, {"name": "My food", "category": FoodItem.PROTEIN})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(FoodItem.objects.filter(name="My food", created_by=self.user).exists())

    def test_rate_limit_does_not_count_items_outside_window(self):
        from django.utils import timezone

        from ants.views import FoodOverviewCreateItemView

        self.client.login(username="tester", password="pass")
        for i in range(FoodOverviewCreateItemView.MAX_CREATIONS_PER_WINDOW):
            item = _make_food(name=f"Old food {i}")
            item.created_by = self.user
            item.save(update_fields=["created_by"])
            FoodItem.objects.filter(pk=item.pk).update(
                created_at=timezone.now() - FoodOverviewCreateItemView.RATE_LIMIT_WINDOW * 2
            )

        response = self.client.post(self.url, {"name": "Fresh food", "category": FoodItem.PROTEIN})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(FoodItem.objects.filter(name="Fresh food", created_by=self.user).exists())


class FoodOverviewNewItemFormViewTest(TestCase):
    def setUp(self):
        self.url = reverse("food_overview_new_item_form")
        self.user = User.objects.create_user(username="tester", password="pass")

    def test_anonymous_redirects_to_login(self):
        response = self.client.get(self.url, {"category": FoodItem.PROTEIN})
        self.assertEqual(response.status_code, 302)

    def test_logged_in_returns_form_prefilled_with_category(self):
        self.client.login(username="tester", password="pass")
        response = self.client.get(self.url, {"category": FoodItem.PROTEIN})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'value="{FoodItem.PROTEIN}"')

    def test_invalid_category_returns_400(self):
        self.client.login(username="tester", password="pass")
        response = self.client.get(self.url, {"category": "BOGUS"})
        self.assertEqual(response.status_code, 400)


class FoodOverviewSuggestSimilarViewTest(TestCase):
    def setUp(self):
        self.url = reverse("food_overview_suggest_similar")
        self.user = User.objects.create_user(username="tester", password="pass")
        _make_food(name="Mealworms", category=FoodItem.PROTEIN)

    def test_anonymous_redirects_to_login(self):
        response = self.client.get(self.url, {"name": "meal"})
        self.assertEqual(response.status_code, 302)

    def test_matches_returned_above_threshold(self):
        self.client.login(username="tester", password="pass")
        response = self.client.get(self.url, {"name": "meal"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mealworms")

    def test_empty_below_threshold(self):
        self.client.login(username="tester", password="pass")
        response = self.client.get(self.url, {"name": "me"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"")
