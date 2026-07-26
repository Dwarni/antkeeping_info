from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.test import TestCase

from ants.admin import FoodItemAdmin
from ants.models import AntSpecies, FoodItem, Genus, SpeciesFoodRating


def _make_species(name="Lasius niger", slug="lasius-niger"):
    genus = Genus.objects.create(name=name.split()[0])
    return AntSpecies.objects.create(name=name, valid=True, genus=genus, slug=slug)


def _make_food(name, category=FoodItem.PROTEIN):
    return FoodItem.objects.create(name=name, category=category)


def _make_vote(species, food_item, user, vote=SpeciesFoodRating.UP):
    return SpeciesFoodRating.objects.create(species=species, food_item=food_item, user=user, vote=vote)


class _FakeMessageStorage:
    def add(self, level, message, extra_tags=""):
        pass


class _FakeRequest:
    """Minimal stand-in so ModelAdmin.message_user() doesn't choke on a bare None."""

    _messages = _FakeMessageStorage()


class MergeFoodItemsActionTest(TestCase):
    def setUp(self):
        self.admin = FoodItemAdmin(FoodItem, AdminSite())
        self.request = _FakeRequest()
        self.species1 = _make_species(name="Lasius niger", slug="lasius-niger")
        self.species2 = _make_species(name="Formica rufa", slug="formica-rufa")
        self.user1 = User.objects.create_user(username="user1", password="pass")
        self.user2 = User.objects.create_user(username="user2", password="pass")

    def test_merge_requires_at_least_two_items(self):
        a = _make_food("Mealworms")
        self.admin.merge_food_items(request=self.request, queryset=FoodItem.objects.filter(pk=a.pk))
        self.assertEqual(FoodItem.objects.count(), 1)

    def test_non_colliding_votes_reassigned_to_survivor(self):
        a = _make_food("Mealworms")
        b = _make_food("Meal worms")
        _make_vote(self.species1, a, self.user1, vote=SpeciesFoodRating.UP)
        _make_vote(self.species2, b, self.user1, vote=SpeciesFoodRating.DOWN)

        self.admin.merge_food_items(request=self.request, queryset=FoodItem.objects.filter(pk__in=[a.pk, b.pk]))

        self.assertFalse(FoodItem.objects.filter(pk=b.pk).exists())
        self.assertEqual(SpeciesFoodRating.objects.filter(food_item=a).count(), 2)

    def test_collision_keeps_more_recently_updated_vote(self):
        a = _make_food("Mealworms")
        b = _make_food("Meal worms")
        older = _make_vote(self.species1, a, self.user1, vote=SpeciesFoodRating.DOWN)
        newer = _make_vote(self.species1, b, self.user1, vote=SpeciesFoodRating.UP)
        # Force a deterministic ordering of updated_at despite auto_now.
        SpeciesFoodRating.objects.filter(pk=older.pk).update(updated_at="2020-01-01T00:00:00Z")
        SpeciesFoodRating.objects.filter(pk=newer.pk).update(updated_at="2024-01-01T00:00:00Z")

        self.admin.merge_food_items(request=self.request, queryset=FoodItem.objects.filter(pk__in=[a.pk, b.pk]))

        ratings = SpeciesFoodRating.objects.filter(species=self.species1, user=self.user1)
        self.assertEqual(ratings.count(), 1)
        self.assertEqual(ratings.first().food_item_id, a.pk)
        self.assertEqual(ratings.first().vote, SpeciesFoodRating.UP)

    def test_collision_keeps_older_vote_when_it_is_more_recently_updated(self):
        a = _make_food("Mealworms")
        b = _make_food("Meal worms")
        survivor_vote = _make_vote(self.species1, a, self.user1, vote=SpeciesFoodRating.UP)
        loser_vote = _make_vote(self.species1, b, self.user1, vote=SpeciesFoodRating.DOWN)
        SpeciesFoodRating.objects.filter(pk=survivor_vote.pk).update(updated_at="2024-01-01T00:00:00Z")
        SpeciesFoodRating.objects.filter(pk=loser_vote.pk).update(updated_at="2020-01-01T00:00:00Z")

        self.admin.merge_food_items(request=self.request, queryset=FoodItem.objects.filter(pk__in=[a.pk, b.pk]))

        ratings = SpeciesFoodRating.objects.filter(species=self.species1, user=self.user1)
        self.assertEqual(ratings.count(), 1)
        self.assertEqual(ratings.first().vote, SpeciesFoodRating.UP)

    def test_merge_three_items_at_once(self):
        a = _make_food("Mealworms")
        b = _make_food("Meal worms")
        c = _make_food("Meelworms")
        _make_vote(self.species1, b, self.user1, vote=SpeciesFoodRating.UP)
        _make_vote(self.species2, c, self.user2, vote=SpeciesFoodRating.DOWN)

        self.admin.merge_food_items(
            request=self.request, queryset=FoodItem.objects.filter(pk__in=[a.pk, b.pk, c.pk])
        )

        self.assertEqual(FoodItem.objects.count(), 1)
        self.assertEqual(FoodItem.objects.first().pk, a.pk)
        self.assertEqual(SpeciesFoodRating.objects.filter(food_item=a).count(), 2)

    def test_admin_created_items_have_no_created_by(self):
        item = _make_food("Mealworms")
        self.assertIsNone(item.created_by)
