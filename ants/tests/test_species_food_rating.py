from django.contrib.auth.models import User
from django.db import IntegrityError
from django.test import TestCase
from django.urls import NoReverseMatch, reverse

from ants.models import AntSpecies, FoodItem, Genus, SpeciesFoodRating


def _make_species(name="Lasius niger", slug="lasius-niger"):
    genus = Genus.objects.create(name=name.split()[0])
    return AntSpecies.objects.create(name=name, valid=True, genus=genus, slug=slug)


def _make_food(name="Mealworms", category=FoodItem.PROTEIN):
    return FoodItem.objects.create(name=name, category=category)


def _make_vote(species, food_item, user, vote=SpeciesFoodRating.UP):
    return SpeciesFoodRating.objects.create(species=species, food_item=food_item, user=user, vote=vote)


class SpeciesFoodRatingModelTest(TestCase):
    def setUp(self):
        self.species = _make_species()
        self.food = _make_food()
        self.user = User.objects.create_user(username="tester", password="pass")

    def test_create_upvote(self):
        rating = _make_vote(self.species, self.food, self.user, vote=SpeciesFoodRating.UP)
        self.assertEqual(rating.vote, SpeciesFoodRating.UP)

    def test_create_downvote(self):
        rating = _make_vote(self.species, self.food, self.user, vote=SpeciesFoodRating.DOWN)
        self.assertEqual(rating.vote, SpeciesFoodRating.DOWN)

    def test_unique_constraint_per_user_species_food_item(self):
        _make_vote(self.species, self.food, self.user)
        with self.assertRaises(IntegrityError):
            SpeciesFoodRating.objects.create(
                species=self.species, food_item=self.food, user=self.user, vote=SpeciesFoodRating.DOWN,
            )

    def test_different_users_can_vote_same_species_and_food(self):
        other = User.objects.create_user(username="other", password="pass")
        _make_vote(self.species, self.food, self.user)
        _make_vote(self.species, self.food, other)
        self.assertEqual(self.species.food_ratings.count(), 2)

    def test_same_user_can_vote_different_food_items(self):
        honey = _make_food(name="Flower honey", category=FoodItem.SUGAR)
        _make_vote(self.species, self.food, self.user)
        _make_vote(self.species, honey, self.user)
        self.assertEqual(SpeciesFoodRating.objects.filter(user=self.user).count(), 2)

    def test_same_user_can_vote_same_food_on_different_species(self):
        other_species = _make_species(name="Formica rufa", slug="formica-rufa")
        _make_vote(self.species, self.food, self.user)
        _make_vote(other_species, self.food, self.user)
        self.assertEqual(SpeciesFoodRating.objects.filter(user=self.user).count(), 2)


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

    def test_context_food_item_no_votes(self):
        _make_food()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        cats = response.context["food_by_category"]
        self.assertEqual(len(cats), 1)
        item_data = cats[0]["items"][0]
        self.assertEqual(item_data["up_count"], 0)
        self.assertEqual(item_data["down_count"], 0)
        self.assertIsNone(item_data["user_vote"])

    def test_context_with_votes(self):
        food = _make_food()
        _make_vote(self.species, food, self.user1, vote=SpeciesFoodRating.UP)
        _make_vote(self.species, food, self.user2, vote=SpeciesFoodRating.UP)
        response = self.client.get(self.url)
        item_data = response.context["food_by_category"][0]["items"][0]
        self.assertEqual(item_data["up_count"], 2)
        self.assertEqual(item_data["down_count"], 0)

    def test_context_mixed_votes(self):
        food = _make_food()
        _make_vote(self.species, food, self.user1, vote=SpeciesFoodRating.UP)
        _make_vote(self.species, food, self.user2, vote=SpeciesFoodRating.DOWN)
        response = self.client.get(self.url)
        item_data = response.context["food_by_category"][0]["items"][0]
        self.assertEqual(item_data["up_count"], 1)
        self.assertEqual(item_data["down_count"], 1)

    def test_context_user_vote_anonymous(self):
        food = _make_food()
        _make_vote(self.species, food, self.user1)
        response = self.client.get(self.url)
        item_data = response.context["food_by_category"][0]["items"][0]
        self.assertIsNone(item_data["user_vote"])

    def test_context_user_vote_logged_in(self):
        food = _make_food()
        rating = _make_vote(self.species, food, self.user1, vote=SpeciesFoodRating.DOWN)
        self.client.login(username="user1", password="pass")
        response = self.client.get(self.url)
        item_data = response.context["food_by_category"][0]["items"][0]
        self.assertEqual(item_data["user_vote"], rating)

    def test_context_user_vote_logged_in_no_own_vote(self):
        food = _make_food()
        _make_vote(self.species, food, self.user2)
        self.client.login(username="user1", password="pass")
        response = self.client.get(self.url)
        item_data = response.context["food_by_category"][0]["items"][0]
        self.assertIsNone(item_data["user_vote"])

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

    def test_rate_food_url_no_longer_exists(self):
        with self.assertRaises(NoReverseMatch):
            reverse("rate_food", args=[self.species.slug])

    def test_vote_buttons_rendered_for_logged_in_user(self):
        _make_food()
        self.client.login(username="user1", password="pass")
        response = self.client.get(self.url)
        self.assertContains(response, reverse("vote_food", args=[self.species.slug, FoodItem.objects.get().pk]))


class SubmitFoodOverviewVoteViewTest(TestCase):
    def setUp(self):
        self.species = _make_species()
        self.food = _make_food()
        self.url = reverse("food_overview_vote")
        self.user = User.objects.create_user(username="tester", password="pass")
        self.client.login(username="tester", password="pass")

    def _post(self, vote, species=None, food_item=None):
        return self.client.post(
            self.url,
            {
                "food_item_id": (food_item or self.food).pk,
                "species_id": (species or self.species).pk,
                "vote": vote,
            },
        )

    def test_login_required(self):
        self.client.logout()
        response = self._post(SpeciesFoodRating.UP)
        self.assertEqual(response.status_code, 302)

    def test_upvote_creates_rating(self):
        response = self._post(SpeciesFoodRating.UP)
        self.assertEqual(response.status_code, 200)
        rating = SpeciesFoodRating.objects.get(species=self.species, food_item=self.food, user=self.user)
        self.assertEqual(rating.vote, SpeciesFoodRating.UP)

    def test_downvote_creates_rating(self):
        response = self._post(SpeciesFoodRating.DOWN)
        self.assertEqual(response.status_code, 200)
        rating = SpeciesFoodRating.objects.get(species=self.species, food_item=self.food, user=self.user)
        self.assertEqual(rating.vote, SpeciesFoodRating.DOWN)

    def test_clicking_same_direction_again_removes_vote(self):
        self._post(SpeciesFoodRating.UP)
        response = self._post(SpeciesFoodRating.UP)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            SpeciesFoodRating.objects.filter(species=self.species, food_item=self.food, user=self.user).exists()
        )

    def test_clicking_opposite_direction_switches_vote(self):
        self._post(SpeciesFoodRating.UP)
        response = self._post(SpeciesFoodRating.DOWN)
        self.assertEqual(response.status_code, 200)
        rating = SpeciesFoodRating.objects.get(species=self.species, food_item=self.food, user=self.user)
        self.assertEqual(rating.vote, SpeciesFoodRating.DOWN)

    def test_invalid_vote_value_returns_400(self):
        response = self.client.post(
            self.url, {"food_item_id": self.food.pk, "species_id": self.species.pk, "vote": 3},
        )
        self.assertEqual(response.status_code, 400)

    def test_missing_species_id_returns_400(self):
        response = self.client.post(self.url, {"food_item_id": self.food.pk, "vote": 1})
        self.assertEqual(response.status_code, 400)

    def test_unknown_species_id_returns_400(self):
        response = self.client.post(
            self.url, {"food_item_id": self.food.pk, "species_id": 999999, "vote": 1},
        )
        self.assertEqual(response.status_code, 400)

    def test_unknown_food_item_id_returns_400(self):
        response = self.client.post(
            self.url, {"food_item_id": 999999, "species_id": self.species.pk, "vote": 1},
        )
        self.assertEqual(response.status_code, 400)


class SubmitSpeciesFoodVoteViewTest(TestCase):
    def setUp(self):
        self.species = _make_species()
        self.food = _make_food()
        self.url = reverse("vote_food", args=[self.species.slug, self.food.pk])
        self.user = User.objects.create_user(username="tester", password="pass")
        self.client.login(username="tester", password="pass")

    def test_login_required(self):
        self.client.logout()
        response = self.client.post(self.url, {"vote": 1})
        self.assertEqual(response.status_code, 302)

    def test_upvote_creates_rating(self):
        response = self.client.post(self.url, {"vote": SpeciesFoodRating.UP})
        self.assertEqual(response.status_code, 200)
        rating = SpeciesFoodRating.objects.get(species=self.species, food_item=self.food, user=self.user)
        self.assertEqual(rating.vote, SpeciesFoodRating.UP)

    def test_toggle_removes_vote(self):
        self.client.post(self.url, {"vote": SpeciesFoodRating.UP})
        response = self.client.post(self.url, {"vote": SpeciesFoodRating.UP})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            SpeciesFoodRating.objects.filter(species=self.species, food_item=self.food, user=self.user).exists()
        )

    def test_invalid_vote_value_returns_400(self):
        response = self.client.post(self.url, {"vote": 99})
        self.assertEqual(response.status_code, 400)


class FoodOverviewAggregationTest(TestCase):
    def setUp(self):
        self.species = _make_species()
        self.species2 = _make_species(name="Formica rufa", slug="formica-rufa")
        self.food = _make_food()
        self.user1 = User.objects.create_user(username="user1", password="pass")
        self.user2 = User.objects.create_user(username="user2", password="pass")

    def test_net_score_across_votes(self):
        _make_vote(self.species, self.food, self.user1, vote=SpeciesFoodRating.UP)
        _make_vote(self.species, self.food, self.user2, vote=SpeciesFoodRating.DOWN)
        response = self.client.get(reverse("food_overview"), {"category": self.food.category})
        food_data = response.context["food_data"][0]
        top_species = {row["species_id"]: row for row in food_data["top_species"]}
        self.assertEqual(top_species[self.species.pk]["net_score"], 0)
        self.assertEqual(top_species[self.species.pk]["up_count"], 1)
        self.assertEqual(top_species[self.species.pk]["down_count"], 1)
        self.assertEqual(food_data["overall_net_score"], 0)
        self.assertEqual(food_data["total_ratings"], 2)

    def test_ranking_by_net_score(self):
        _make_vote(self.species, self.food, self.user1, vote=SpeciesFoodRating.DOWN)
        _make_vote(self.species2, self.food, self.user1, vote=SpeciesFoodRating.UP)
        response = self.client.get(reverse("food_overview"), {"category": self.food.category})
        food_data = response.context["food_data"][0]
        self.assertEqual(food_data["top_species"][0]["species_id"], self.species2.pk)
