from django.contrib.auth.models import User
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse

from ants.models import AntSpecies, FoodItem, Genus, SpeciesFoodRating


def _make_species(name="Lasius niger", slug="lasius-niger"):
    genus = Genus.objects.create(name=name.split()[0])
    return AntSpecies.objects.create(name=name, valid=True, genus=genus, slug=slug)


def _make_food(name="Mealworms", category=FoodItem.PROTEIN):
    return FoodItem.objects.create(name=name, category=category)


class SpeciesFoodRatingModelTest(TestCase):
    def setUp(self):
        self.species = _make_species()
        self.food = _make_food()
        self.user = User.objects.create_user(username="tester", password="pass")

    def test_create_rating(self):
        rating = SpeciesFoodRating.objects.create(
            species=self.species,
            food_item=self.food,
            user=self.user,
            acceptance=SpeciesFoodRating.THREE_STARS,
        )
        self.assertEqual(rating.acceptance, SpeciesFoodRating.THREE_STARS)
        self.assertEqual(rating.comment, "")

    def test_create_rating_with_comment(self):
        rating = SpeciesFoodRating.objects.create(
            species=self.species,
            food_item=self.food,
            user=self.user,
            acceptance=SpeciesFoodRating.TWO_STARS,
            comment="Ate it slowly.",
        )
        self.assertEqual(rating.comment, "Ate it slowly.")

    def test_unique_constraint_per_user_species_food_item(self):
        SpeciesFoodRating.objects.create(
            species=self.species,
            food_item=self.food,
            user=self.user,
            acceptance=SpeciesFoodRating.THREE_STARS,
        )
        with self.assertRaises(IntegrityError):
            SpeciesFoodRating.objects.create(
                species=self.species,
                food_item=self.food,
                user=self.user,
                acceptance=SpeciesFoodRating.ONE_STAR,
            )

    def test_different_users_can_rate_same_species_and_food(self):
        other = User.objects.create_user(username="other", password="pass")
        SpeciesFoodRating.objects.create(
            species=self.species, food_item=self.food, user=self.user,
            acceptance=SpeciesFoodRating.THREE_STARS,
        )
        SpeciesFoodRating.objects.create(
            species=self.species, food_item=self.food, user=other,
            acceptance=SpeciesFoodRating.ONE_STAR,
        )
        self.assertEqual(self.species.food_ratings.count(), 2)

    def test_same_user_can_rate_different_food_items(self):
        honey = _make_food(name="Flower honey", category=FoodItem.SUGAR)
        SpeciesFoodRating.objects.create(
            species=self.species, food_item=self.food, user=self.user,
            acceptance=SpeciesFoodRating.THREE_STARS,
        )
        SpeciesFoodRating.objects.create(
            species=self.species, food_item=honey, user=self.user,
            acceptance=SpeciesFoodRating.THREE_STARS,
        )
        self.assertEqual(SpeciesFoodRating.objects.filter(user=self.user).count(), 2)

    def test_same_user_can_rate_same_food_on_different_species(self):
        other_species = _make_species(name="Formica rufa", slug="formica-rufa")
        SpeciesFoodRating.objects.create(
            species=self.species, food_item=self.food, user=self.user,
            acceptance=SpeciesFoodRating.THREE_STARS,
        )
        SpeciesFoodRating.objects.create(
            species=other_species, food_item=self.food, user=self.user,
            acceptance=SpeciesFoodRating.ONE_STAR,
        )
        self.assertEqual(SpeciesFoodRating.objects.filter(user=self.user).count(), 2)

    def test_create_rating_with_condition(self):
        rating = SpeciesFoodRating.objects.create(
            species=self.species,
            food_item=self.food,
            user=self.user,
            acceptance=SpeciesFoodRating.THREE_STARS,
            condition=SpeciesFoodRating.ALIVE,
        )
        self.assertEqual(rating.condition, SpeciesFoodRating.ALIVE)

    def test_condition_optional_at_model_level(self):
        rating = SpeciesFoodRating.objects.create(
            species=self.species,
            food_item=self.food,
            user=self.user,
            acceptance=SpeciesFoodRating.THREE_STARS,
        )
        self.assertIsNone(rating.condition)

    def test_conditions_for_category_protein(self):
        self.assertEqual(
            SpeciesFoodRating.conditions_for_category(FoodItem.PROTEIN),
            [
                SpeciesFoodRating.ALIVE,
                SpeciesFoodRating.FRESHLY_KILLED,
                SpeciesFoodRating.SCALDED,
                SpeciesFoodRating.FROZEN,
                SpeciesFoodRating.DRIED,
            ],
        )

    def test_conditions_for_category_plant(self):
        self.assertEqual(
            SpeciesFoodRating.conditions_for_category(FoodItem.PLANT),
            [SpeciesFoodRating.FRESH, SpeciesFoodRating.FROZEN, SpeciesFoodRating.DRIED],
        )

    def test_conditions_for_category_not_applicable(self):
        for category in (FoodItem.SEEDS, FoodItem.SUGAR, FoodItem.OTHER):
            self.assertEqual(SpeciesFoodRating.conditions_for_category(category), [])


class AntSpeciesDetailFoodContextTest(TestCase):
    def setUp(self):
        self.species = _make_species()
        self.url = reverse("ant_detail", args=[self.species.slug])
        self.user1 = User.objects.create_user(username="user1", password="pass")
        self.user2 = User.objects.create_user(username="user2", password="pass")

    def test_context_no_food_items(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["food_by_category"], [])

    def test_context_food_item_no_ratings(self):
        _make_food()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        cats = response.context["food_by_category"]
        self.assertEqual(len(cats), 1)
        item_data = cats[0]["items"][0]
        self.assertEqual(item_data["total"], 0)
        self.assertIsNone(item_data["avg"])
        self.assertIsNone(item_data["user_rating"])

    def test_context_with_ratings(self):
        food = _make_food()
        SpeciesFoodRating.objects.create(
            species=self.species, food_item=food, user=self.user1,
            acceptance=SpeciesFoodRating.THREE_STARS,
        )
        SpeciesFoodRating.objects.create(
            species=self.species, food_item=food, user=self.user2,
            acceptance=SpeciesFoodRating.THREE_STARS,
        )
        response = self.client.get(self.url)
        item_data = response.context["food_by_category"][0]["items"][0]
        self.assertEqual(item_data["total"], 2)
        self.assertEqual(item_data["avg"], 3.0)

    def test_context_avg_mixed_ratings(self):
        food = _make_food()
        SpeciesFoodRating.objects.create(
            species=self.species, food_item=food, user=self.user1,
            acceptance=SpeciesFoodRating.ONE_STAR,
        )
        SpeciesFoodRating.objects.create(
            species=self.species, food_item=food, user=self.user2,
            acceptance=SpeciesFoodRating.FIVE_STARS,
        )
        response = self.client.get(self.url)
        item_data = response.context["food_by_category"][0]["items"][0]
        self.assertEqual(item_data["total"], 2)
        self.assertEqual(item_data["avg"], 3.0)

    def test_context_user_rating_anonymous(self):
        food = _make_food()
        SpeciesFoodRating.objects.create(
            species=self.species, food_item=food, user=self.user1,
            acceptance=SpeciesFoodRating.THREE_STARS,
        )
        response = self.client.get(self.url)
        item_data = response.context["food_by_category"][0]["items"][0]
        self.assertIsNone(item_data["user_rating"])

    def test_context_user_rating_logged_in(self):
        food = _make_food()
        rating = SpeciesFoodRating.objects.create(
            species=self.species, food_item=food, user=self.user1,
            acceptance=SpeciesFoodRating.TWO_STARS,
        )
        self.client.login(username="user1", password="pass")
        response = self.client.get(self.url)
        item_data = response.context["food_by_category"][0]["items"][0]
        self.assertEqual(item_data["user_rating"], rating)

    def test_context_user_rating_logged_in_no_own_rating(self):
        food = _make_food()
        SpeciesFoodRating.objects.create(
            species=self.species, food_item=food, user=self.user2,
            acceptance=SpeciesFoodRating.THREE_STARS,
        )
        self.client.login(username="user1", password="pass")
        response = self.client.get(self.url)
        item_data = response.context["food_by_category"][0]["items"][0]
        self.assertIsNone(item_data["user_rating"])

    def test_category_grouping(self):
        _make_food(name="Mealworms", category=FoodItem.PROTEIN)
        _make_food(name="Flower honey", category=FoodItem.SUGAR)
        response = self.client.get(self.url)
        cats = response.context["food_by_category"]
        self.assertEqual(len(cats), 2)
        category_keys = [c["category_key"] for c in cats]
        self.assertIn(FoodItem.PROTEIN, category_keys)
        self.assertIn(FoodItem.SUGAR, category_keys)

    def test_category_order_follows_choices(self):
        _make_food(name="Sunflower seeds", category=FoodItem.SEEDS)
        _make_food(name="Mealworms", category=FoodItem.PROTEIN)
        response = self.client.get(self.url)
        cats = response.context["food_by_category"]
        self.assertEqual(cats[0]["category_key"], FoodItem.PROTEIN)
        self.assertEqual(cats[1]["category_key"], FoodItem.SEEDS)


class SubmitFoodRatingViewTest(TestCase):
    def setUp(self):
        self.species = _make_species()
        self.food = _make_food()
        self.url = reverse("rate_food", args=[self.species.slug])
        self.user = User.objects.create_user(username="tester", password="pass")

    def test_anonymous_redirects_to_login(self):
        response = self.client.post(self.url, {"food_item_id": self.food.pk, "acceptance": 3})
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/", response["Location"])

    def test_logged_in_creates_rating(self):
        self.client.login(username="tester", password="pass")
        response = self.client.post(
            self.url,
            {
                "food_item_id": self.food.pk,
                "acceptance": 3,
                "condition": SpeciesFoodRating.ALIVE,
                "comment": "gobbled it up",
            },
        )
        self.assertEqual(response.status_code, 200)
        rating = SpeciesFoodRating.objects.get(species=self.species, food_item=self.food, user=self.user)
        self.assertEqual(rating.acceptance, SpeciesFoodRating.THREE_STARS)
        self.assertEqual(rating.comment, "gobbled it up")

    def test_second_post_updates_existing_rating(self):
        self.client.login(username="tester", password="pass")
        self.client.post(
            self.url,
            {"food_item_id": self.food.pk, "acceptance": 3, "condition": SpeciesFoodRating.ALIVE},
        )
        self.client.post(
            self.url,
            {
                "food_item_id": self.food.pk,
                "acceptance": 1,
                "condition": SpeciesFoodRating.DRIED,
                "comment": "ignored",
            },
        )
        self.assertEqual(
            SpeciesFoodRating.objects.filter(species=self.species, food_item=self.food, user=self.user).count(),
            1,
        )
        rating = SpeciesFoodRating.objects.get(species=self.species, food_item=self.food, user=self.user)
        self.assertEqual(rating.acceptance, SpeciesFoodRating.ONE_STAR)
        self.assertEqual(rating.comment, "ignored")

    def test_four_and_five_star_ratings_accepted(self):
        self.client.login(username="tester", password="pass")
        response = self.client.post(
            self.url,
            {"food_item_id": self.food.pk, "acceptance": 4, "condition": SpeciesFoodRating.ALIVE},
        )
        self.assertEqual(response.status_code, 200)
        self.client.post(
            self.url,
            {"food_item_id": self.food.pk, "acceptance": 5, "condition": SpeciesFoodRating.ALIVE},
        )
        rating = SpeciesFoodRating.objects.get(species=self.species, food_item=self.food, user=self.user)
        self.assertEqual(rating.acceptance, SpeciesFoodRating.FIVE_STARS)

    def test_invalid_acceptance_returns_400(self):
        self.client.login(username="tester", password="pass")
        response = self.client.post(self.url, {"food_item_id": self.food.pk, "acceptance": 99})
        self.assertEqual(response.status_code, 400)

    def test_acceptance_6_returns_400(self):
        self.client.login(username="tester", password="pass")
        response = self.client.post(self.url, {"food_item_id": self.food.pk, "acceptance": 6})
        self.assertEqual(response.status_code, 400)

    def test_missing_acceptance_returns_400(self):
        self.client.login(username="tester", password="pass")
        response = self.client.post(self.url, {"food_item_id": self.food.pk})
        self.assertEqual(response.status_code, 400)

    def test_invalid_food_item_id_returns_400(self):
        self.client.login(username="tester", password="pass")
        response = self.client.post(self.url, {"food_item_id": 99999, "acceptance": 3})
        self.assertEqual(response.status_code, 400)

    def test_missing_food_item_id_returns_400(self):
        self.client.login(username="tester", password="pass")
        response = self.client.post(self.url, {"acceptance": 3})
        self.assertEqual(response.status_code, 400)

    def test_response_contains_food_ratings_section(self):
        self.client.login(username="tester", password="pass")
        response = self.client.post(
            self.url,
            {"food_item_id": self.food.pk, "acceptance": 3, "condition": SpeciesFoodRating.ALIVE},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="food-ratings-section"')

    def test_response_contains_food_item_name(self):
        self.client.login(username="tester", password="pass")
        response = self.client.post(
            self.url,
            {"food_item_id": self.food.pk, "acceptance": 3, "condition": SpeciesFoodRating.ALIVE},
        )
        self.assertContains(response, self.food.name)

    def test_protein_food_missing_condition_returns_400(self):
        self.client.login(username="tester", password="pass")
        response = self.client.post(self.url, {"food_item_id": self.food.pk, "acceptance": 3})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(
            SpeciesFoodRating.objects.filter(species=self.species, food_item=self.food).exists()
        )

    def test_protein_food_invalid_condition_returns_400(self):
        self.client.login(username="tester", password="pass")
        response = self.client.post(
            self.url,
            {"food_item_id": self.food.pk, "acceptance": 3, "condition": SpeciesFoodRating.FRESH},
        )
        self.assertEqual(response.status_code, 400)

    def test_protein_food_valid_condition_accepted(self):
        self.client.login(username="tester", password="pass")
        response = self.client.post(
            self.url,
            {"food_item_id": self.food.pk, "acceptance": 3, "condition": SpeciesFoodRating.FROZEN},
        )
        self.assertEqual(response.status_code, 200)
        rating = SpeciesFoodRating.objects.get(species=self.species, food_item=self.food, user=self.user)
        self.assertEqual(rating.condition, SpeciesFoodRating.FROZEN)

    def test_plant_food_missing_condition_returns_400(self):
        leaf = _make_food(name="Bramble leaf", category=FoodItem.PLANT)
        self.client.login(username="tester", password="pass")
        response = self.client.post(self.url, {"food_item_id": leaf.pk, "acceptance": 3})
        self.assertEqual(response.status_code, 400)

    def test_plant_food_invalid_condition_returns_400(self):
        leaf = _make_food(name="Bramble leaf", category=FoodItem.PLANT)
        self.client.login(username="tester", password="pass")
        response = self.client.post(
            self.url,
            {"food_item_id": leaf.pk, "acceptance": 3, "condition": SpeciesFoodRating.SCALDED},
        )
        self.assertEqual(response.status_code, 400)

    def test_plant_food_valid_condition_accepted(self):
        leaf = _make_food(name="Bramble leaf", category=FoodItem.PLANT)
        self.client.login(username="tester", password="pass")
        response = self.client.post(
            self.url,
            {"food_item_id": leaf.pk, "acceptance": 3, "condition": SpeciesFoodRating.FRESH},
        )
        self.assertEqual(response.status_code, 200)
        rating = SpeciesFoodRating.objects.get(species=self.species, food_item=leaf, user=self.user)
        self.assertEqual(rating.condition, SpeciesFoodRating.FRESH)

    def test_seeds_food_condition_not_required(self):
        seeds = _make_food(name="Sunflower seeds", category=FoodItem.SEEDS)
        self.client.login(username="tester", password="pass")
        response = self.client.post(self.url, {"food_item_id": seeds.pk, "acceptance": 3})
        self.assertEqual(response.status_code, 200)

    def test_seeds_food_stray_condition_is_ignored(self):
        seeds = _make_food(name="Sunflower seeds", category=FoodItem.SEEDS)
        self.client.login(username="tester", password="pass")
        response = self.client.post(
            self.url,
            {"food_item_id": seeds.pk, "acceptance": 3, "condition": SpeciesFoodRating.ALIVE},
        )
        self.assertEqual(response.status_code, 200)
        rating = SpeciesFoodRating.objects.get(species=self.species, food_item=seeds, user=self.user)
        self.assertIsNone(rating.condition)

    def test_other_food_condition_not_required(self):
        other = _make_food(name="Sausage", category=FoodItem.OTHER)
        self.client.login(username="tester", password="pass")
        response = self.client.post(self.url, {"food_item_id": other.pk, "acceptance": 3})
        self.assertEqual(response.status_code, 200)


class SubmitFoodRatingFromOverviewViewTest(TestCase):
    def setUp(self):
        self.species = _make_species()
        self.food = _make_food()
        self.url = reverse("food_overview_rate")
        self.user = User.objects.create_user(username="tester", password="pass")
        self.client.login(username="tester", password="pass")

    def test_protein_food_missing_condition_returns_400(self):
        response = self.client.post(
            self.url,
            {"species_id": self.species.pk, "food_item_id": self.food.pk, "acceptance": 3},
        )
        self.assertEqual(response.status_code, 400)

    def test_protein_food_invalid_condition_returns_400(self):
        response = self.client.post(
            self.url,
            {
                "species_id": self.species.pk,
                "food_item_id": self.food.pk,
                "acceptance": 3,
                "condition": SpeciesFoodRating.FRESH,
            },
        )
        self.assertEqual(response.status_code, 400)

    def test_protein_food_valid_condition_accepted(self):
        response = self.client.post(
            self.url,
            {
                "species_id": self.species.pk,
                "food_item_id": self.food.pk,
                "acceptance": 3,
                "condition": SpeciesFoodRating.FROZEN,
            },
        )
        self.assertEqual(response.status_code, 200)
        rating = SpeciesFoodRating.objects.get(species=self.species, food_item=self.food, user=self.user)
        self.assertEqual(rating.condition, SpeciesFoodRating.FROZEN)

    def test_plant_food_missing_condition_returns_400(self):
        leaf = _make_food(name="Bramble leaf", category=FoodItem.PLANT)
        response = self.client.post(
            self.url,
            {"species_id": self.species.pk, "food_item_id": leaf.pk, "acceptance": 3},
        )
        self.assertEqual(response.status_code, 400)

    def test_plant_food_valid_condition_accepted(self):
        leaf = _make_food(name="Bramble leaf", category=FoodItem.PLANT)
        response = self.client.post(
            self.url,
            {
                "species_id": self.species.pk,
                "food_item_id": leaf.pk,
                "acceptance": 3,
                "condition": SpeciesFoodRating.FRESH,
            },
        )
        self.assertEqual(response.status_code, 200)
        rating = SpeciesFoodRating.objects.get(species=self.species, food_item=leaf, user=self.user)
        self.assertEqual(rating.condition, SpeciesFoodRating.FRESH)

    def test_seeds_food_condition_not_required(self):
        seeds = _make_food(name="Sunflower seeds", category=FoodItem.SEEDS)
        response = self.client.post(
            self.url,
            {"species_id": self.species.pk, "food_item_id": seeds.pk, "acceptance": 3},
        )
        self.assertEqual(response.status_code, 200)
        rating = SpeciesFoodRating.objects.get(species=self.species, food_item=seeds, user=self.user)
        self.assertIsNone(rating.condition)
