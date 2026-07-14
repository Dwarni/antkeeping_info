from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.test import TestCase

from ants.admin import FoodItemAdmin
from ants.models import AntSpecies, FoodItem, FoodRatingSubmission, Genus, SpeciesFoodRating


def _make_species(name="Lasius niger", slug="lasius-niger"):
    genus = Genus.objects.create(name=name.split()[0])
    return AntSpecies.objects.create(name=name, valid=True, genus=genus, slug=slug)


def _make_food(name, category=FoodItem.PROTEIN):
    return FoodItem.objects.create(name=name, category=category)


def _make_rating(species, food_item, user, acceptance=3, comment=""):
    submission = FoodRatingSubmission.objects.create(
        food_item=food_item, user=user, acceptance=acceptance, comment=comment,
    )
    return SpeciesFoodRating.objects.create(
        species=species, food_item=food_item, user=user, submission=submission,
    )


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

    def test_non_colliding_ratings_reassigned_to_survivor(self):
        a = _make_food("Mealworms")
        b = _make_food("Meal worms")
        _make_rating(self.species1, a, self.user1, acceptance=3)
        _make_rating(self.species2, b, self.user1, acceptance=4)

        self.admin.merge_food_items(request=self.request, queryset=FoodItem.objects.filter(pk__in=[a.pk, b.pk]))

        self.assertFalse(FoodItem.objects.filter(pk=b.pk).exists())
        self.assertEqual(SpeciesFoodRating.objects.filter(food_item=a).count(), 2)

    def test_collision_keeps_higher_acceptance(self):
        a = _make_food("Mealworms")
        b = _make_food("Meal worms")
        _make_rating(self.species1, a, self.user1, acceptance=2)
        _make_rating(self.species1, b, self.user1, acceptance=4)

        self.admin.merge_food_items(request=self.request, queryset=FoodItem.objects.filter(pk__in=[a.pk, b.pk]))

        ratings = SpeciesFoodRating.objects.filter(species=self.species1, user=self.user1)
        self.assertEqual(ratings.count(), 1)
        self.assertEqual(ratings.first().food_item_id, a.pk)
        self.assertEqual(ratings.first().submission.acceptance, 4)

    def test_collision_tie_keeps_most_recently_updated(self):
        a = _make_food("Mealworms")
        b = _make_food("Meal worms")
        older = _make_rating(self.species1, a, self.user1, acceptance=3, comment="older")
        newer = _make_rating(self.species1, b, self.user1, acceptance=3, comment="newer")
        # Force a deterministic ordering of updated_at despite auto_now.
        FoodRatingSubmission.objects.filter(pk=older.submission_id).update(updated_at="2020-01-01T00:00:00Z")
        FoodRatingSubmission.objects.filter(pk=newer.submission_id).update(updated_at="2024-01-01T00:00:00Z")

        self.admin.merge_food_items(request=self.request, queryset=FoodItem.objects.filter(pk__in=[a.pk, b.pk]))

        ratings = SpeciesFoodRating.objects.filter(species=self.species1, user=self.user1)
        self.assertEqual(ratings.count(), 1)
        self.assertEqual(ratings.first().submission.comment, "newer")
        self.assertEqual(ratings.first().food_item_id, a.pk)

    def test_merge_three_items_at_once(self):
        a = _make_food("Mealworms")
        b = _make_food("Meal worms")
        c = _make_food("Meelworms")
        _make_rating(self.species1, b, self.user1, acceptance=3)
        _make_rating(self.species2, c, self.user2, acceptance=5)

        self.admin.merge_food_items(
            request=self.request, queryset=FoodItem.objects.filter(pk__in=[a.pk, b.pk, c.pk])
        )

        self.assertEqual(FoodItem.objects.count(), 1)
        self.assertEqual(FoodItem.objects.first().pk, a.pk)
        self.assertEqual(SpeciesFoodRating.objects.filter(food_item=a).count(), 2)

    def test_partial_collision_splits_loser_submission(self):
        # Loser submission b covers species1 (collides) and species2 (no collision).
        a = _make_food("Mealworms")
        b = _make_food("Meal worms")
        _make_rating(self.species1, a, self.user1, acceptance=4)  # survivor-side, wins collision

        loser_submission = FoodRatingSubmission.objects.create(food_item=b, user=self.user1, acceptance=2)
        SpeciesFoodRating.objects.create(species=self.species1, food_item=b, user=self.user1, submission=loser_submission)
        SpeciesFoodRating.objects.create(species=self.species2, food_item=b, user=self.user1, submission=loser_submission)

        self.admin.merge_food_items(request=self.request, queryset=FoodItem.objects.filter(pk__in=[a.pk, b.pk]))

        # species1's rating stays at acceptance=4 (the survivor-side winner).
        s1_rating = SpeciesFoodRating.objects.get(species=self.species1, food_item=a, user=self.user1)
        self.assertEqual(s1_rating.submission.acceptance, 4)
        # species2 (non-colliding) keeps the loser submission, now reassigned to the survivor.
        s2_rating = SpeciesFoodRating.objects.get(species=self.species2, food_item=a, user=self.user1)
        self.assertEqual(s2_rating.submission_id, loser_submission.pk)
        self.assertEqual(s2_rating.submission.acceptance, 2)
        # The loser submission survives (still referenced by species2) but now points at the survivor food item.
        loser_submission.refresh_from_db()
        self.assertEqual(loser_submission.food_item_id, a.pk)

    def test_full_collision_deletes_loser_submission(self):
        a = _make_food("Mealworms")
        b = _make_food("Meal worms")
        _make_rating(self.species1, a, self.user1, acceptance=5)
        loser = _make_rating(self.species1, b, self.user1, acceptance=1)
        loser_submission_id = loser.submission_id

        self.admin.merge_food_items(request=self.request, queryset=FoodItem.objects.filter(pk__in=[a.pk, b.pk]))

        self.assertFalse(FoodRatingSubmission.objects.filter(pk=loser_submission_id).exists())

    def test_admin_created_items_have_no_created_by(self):
        item = _make_food("Mealworms")
        self.assertIsNone(item.created_by)
