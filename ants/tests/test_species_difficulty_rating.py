from django.contrib.auth.models import User
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse

from ants.models import AntSpecies, Genus, SpeciesDifficultyRating


def _make_species(name="Lasius niger", slug="lasius-niger"):
    genus = Genus.objects.create(name=name.split()[0])
    return AntSpecies.objects.create(name=name, valid=True, genus=genus, slug=slug)


class SpeciesDifficultyRatingModelTest(TestCase):
    def setUp(self):
        self.species = _make_species()
        self.user = User.objects.create_user(username="tester", password="pass")

    def test_create_rating(self):
        rating = SpeciesDifficultyRating.objects.create(
            species=self.species,
            user=self.user,
            difficulty=SpeciesDifficultyRating.BEGINNER,
        )
        self.assertEqual(rating.difficulty, SpeciesDifficultyRating.BEGINNER)
        self.assertEqual(rating.comment, "")

    def test_create_rating_with_comment(self):
        rating = SpeciesDifficultyRating.objects.create(
            species=self.species,
            user=self.user,
            difficulty=SpeciesDifficultyRating.INTERMEDIATE,
            comment="Easy to start but needs stable temps.",
        )
        self.assertEqual(rating.comment, "Easy to start but needs stable temps.")

    def test_unique_constraint_per_user_and_species(self):
        SpeciesDifficultyRating.objects.create(
            species=self.species,
            user=self.user,
            difficulty=SpeciesDifficultyRating.BEGINNER,
        )
        with self.assertRaises(IntegrityError):
            SpeciesDifficultyRating.objects.create(
                species=self.species,
                user=self.user,
                difficulty=SpeciesDifficultyRating.ADVANCED,
            )

    def test_different_users_can_rate_same_species(self):
        other = User.objects.create_user(username="other", password="pass")
        SpeciesDifficultyRating.objects.create(
            species=self.species, user=self.user, difficulty=SpeciesDifficultyRating.BEGINNER
        )
        SpeciesDifficultyRating.objects.create(
            species=self.species, user=other, difficulty=SpeciesDifficultyRating.EXPERT
        )
        self.assertEqual(self.species.difficulty_ratings.count(), 2)

    def test_same_user_can_rate_different_species(self):
        other_species = _make_species(name="Formica rufa", slug="formica-rufa")
        SpeciesDifficultyRating.objects.create(
            species=self.species, user=self.user, difficulty=SpeciesDifficultyRating.BEGINNER
        )
        SpeciesDifficultyRating.objects.create(
            species=other_species, user=self.user, difficulty=SpeciesDifficultyRating.EXPERT
        )
        self.assertEqual(SpeciesDifficultyRating.objects.filter(user=self.user).count(), 2)


class AntSpeciesDetailDifficultyContextTest(TestCase):
    def setUp(self):
        self.species = _make_species()
        self.url = reverse("ant_detail", args=[self.species.slug])
        self.user1 = User.objects.create_user(username="user1", password="pass")
        self.user2 = User.objects.create_user(username="user2", password="pass")
        self.user3 = User.objects.create_user(username="user3", password="pass")

    def test_context_no_ratings(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["difficulty_total"], 0)
        self.assertIsNone(response.context["difficulty_avg"])
        self.assertIsNone(response.context["dominant_difficulty_level"])
        self.assertIsNone(response.context["user_difficulty_rating"])

    def test_context_with_ratings(self):
        SpeciesDifficultyRating.objects.create(
            species=self.species, user=self.user1, difficulty=SpeciesDifficultyRating.INTERMEDIATE
        )
        SpeciesDifficultyRating.objects.create(
            species=self.species, user=self.user2, difficulty=SpeciesDifficultyRating.INTERMEDIATE
        )
        SpeciesDifficultyRating.objects.create(
            species=self.species, user=self.user3, difficulty=SpeciesDifficultyRating.ADVANCED
        )
        response = self.client.get(self.url)
        self.assertEqual(response.context["difficulty_total"], 3)
        # avg = (2+2+3)/3 = 2.33… → rounded to 1 decimal = 2.3
        self.assertAlmostEqual(response.context["difficulty_avg"], 2.3, places=1)
        self.assertEqual(
            response.context["dominant_difficulty_level"],
            SpeciesDifficultyRating.INTERMEDIATE,
        )

    def test_context_user_rating_anonymous(self):
        SpeciesDifficultyRating.objects.create(
            species=self.species, user=self.user1, difficulty=SpeciesDifficultyRating.BEGINNER
        )
        response = self.client.get(self.url)
        self.assertIsNone(response.context["user_difficulty_rating"])

    def test_context_user_rating_logged_in(self):
        rating = SpeciesDifficultyRating.objects.create(
            species=self.species, user=self.user1, difficulty=SpeciesDifficultyRating.ADVANCED
        )
        self.client.login(username="user1", password="pass")
        response = self.client.get(self.url)
        self.assertEqual(response.context["user_difficulty_rating"], rating)

    def test_context_user_rating_logged_in_no_own_rating(self):
        SpeciesDifficultyRating.objects.create(
            species=self.species, user=self.user2, difficulty=SpeciesDifficultyRating.ADVANCED
        )
        self.client.login(username="user1", password="pass")
        response = self.client.get(self.url)
        self.assertIsNone(response.context["user_difficulty_rating"])

    def test_distribution_counts(self):
        SpeciesDifficultyRating.objects.create(
            species=self.species, user=self.user1, difficulty=SpeciesDifficultyRating.BEGINNER
        )
        SpeciesDifficultyRating.objects.create(
            species=self.species, user=self.user2, difficulty=SpeciesDifficultyRating.EXPERT
        )
        response = self.client.get(self.url)
        dist = response.context["difficulty_distribution"]
        self.assertEqual(dist[SpeciesDifficultyRating.BEGINNER], 1)
        self.assertEqual(dist[SpeciesDifficultyRating.INTERMEDIATE], 0)
        self.assertEqual(dist[SpeciesDifficultyRating.ADVANCED], 0)
        self.assertEqual(dist[SpeciesDifficultyRating.EXPERT], 1)


class SubmitDifficultyRatingViewTest(TestCase):
    def setUp(self):
        self.species = _make_species()
        self.url = reverse("rate_difficulty", args=[self.species.slug])
        self.user = User.objects.create_user(username="tester", password="pass")

    def test_anonymous_redirects_to_login(self):
        response = self.client.post(self.url, {"difficulty": 1})
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/", response["Location"])

    def test_logged_in_creates_rating(self):
        self.client.login(username="tester", password="pass")
        response = self.client.post(self.url, {"difficulty": 2, "comment": "manageable"})
        self.assertEqual(response.status_code, 200)
        rating = SpeciesDifficultyRating.objects.get(species=self.species, user=self.user)
        self.assertEqual(rating.difficulty, SpeciesDifficultyRating.INTERMEDIATE)
        self.assertEqual(rating.comment, "manageable")

    def test_second_post_updates_existing_rating(self):
        self.client.login(username="tester", password="pass")
        self.client.post(self.url, {"difficulty": 1})
        self.client.post(self.url, {"difficulty": 4, "comment": "very hard"})
        self.assertEqual(
            SpeciesDifficultyRating.objects.filter(species=self.species, user=self.user).count(),
            1,
        )
        rating = SpeciesDifficultyRating.objects.get(species=self.species, user=self.user)
        self.assertEqual(rating.difficulty, SpeciesDifficultyRating.EXPERT)
        self.assertEqual(rating.comment, "very hard")

    def test_invalid_difficulty_returns_400(self):
        self.client.login(username="tester", password="pass")
        response = self.client.post(self.url, {"difficulty": 99})
        self.assertEqual(response.status_code, 400)

    def test_missing_difficulty_returns_400(self):
        self.client.login(username="tester", password="pass")
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, 400)

    def test_response_contains_updated_section(self):
        self.client.login(username="tester", password="pass")
        response = self.client.post(self.url, {"difficulty": 3})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="difficulty-rating-section"')
        self.assertContains(response, "Advanced")
