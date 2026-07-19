from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from ants.models import AntSpecies, SpeciesFoodRating


class AntSpeciesSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return AntSpecies.objects.all()

    def lastmod(self, obj):
        return getattr(obj, "updated_at", None)


class StaticViewSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.6

    def items(self):
        return [
            "home",
            "food_overview",
            "nuptial_flight_table",
            "forbidden_in_eu_species_list",
            "species_filter",
            "size_comparison",
            "antdb_top_lists",
            "flights_map",
            "flights_list",
            "flights_top_lists",
            "contact",
        ]

    def location(self, item):
        return reverse(item)


class TaxonomicRanksByRegionSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.6

    def items(self):
        return ["species", "genera", "tribes", "sub-families"]

    def location(self, item):
        return reverse("taxonomic_ranks_by_region", args=[item])


class FoodItemSpeciesRatingSitemap(Sitemap):
    """One entry per (food item, species) pair that has at least one rating."""

    changefreq = "monthly"
    priority = 0.4

    def items(self):
        return (
            SpeciesFoodRating.objects.values_list("food_item_id", "species__slug")
            .distinct()
            .order_by("food_item_id", "species__slug")
        )

    def location(self, item):
        food_item_id, species_slug = item
        return reverse("food_item_species_ratings", args=[food_item_id, species_slug])
