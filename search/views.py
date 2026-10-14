"""Views for the global search app."""

import difflib
from django.core.cache import cache
from django.db.models import Q
from django.http import JsonResponse
from django.urls import reverse
from django.views.generic import TemplateView, View

from ants.models import (
    AntRegion,
    AntSpecies,
    ColonyJournalEntry,
    CommonName,
    FoodItem,
)

POPULAR_SEARCHES = [
    "Lasius niger",
    "Messor barbarus",
    "Camponotus",
    "Formica",
    "Honigwasser",
    "Schwarze Wegameise",
    "Deutschland",
]


def _find_did_you_mean(query):
    """Return a close spelling suggestion for query if one exists."""
    if not query or len(query) < 3:
        return None

    from ants.models import Genus

    # 1. Check genera first (fast: 348 items)
    genera = cache.get("search_genera_candidates")
    if genera is None:
        genera = list(Genus.objects.values_list("name", flat=True))
        cache.set("search_genera_candidates", genera, 86400)

    genus_match = difflib.get_close_matches(query.capitalize(), genera, n=1, cutoff=0.7)
    if genus_match and genus_match[0].lower() != query.lower():
        return genus_match[0]

    # 2. Check full species names, common names & food items
    candidates = cache.get("search_full_candidates")
    if candidates is None:
        species_names = list(
            AntSpecies.objects.filter(valid=True).values_list("name", flat=True)
        )
        common_names = list(CommonName.objects.values_list("name", flat=True))
        food_names = list(FoodItem.objects.values_list("name", flat=True))
        candidates = species_names + common_names + food_names
        cache.set("search_full_candidates", candidates, 86400)

    matches = difflib.get_close_matches(query, candidates, n=1, cutoff=0.65)
    if not matches:
        matches = difflib.get_close_matches(query.title(), candidates, n=1, cutoff=0.65)
    if matches and matches[0].lower() != query.lower():
        return matches[0]

    return None


class SearchView(TemplateView):
    """
    Global multi-category search view.
    Categorizes results into Ant Species, Community Journals, Food Database, and Regions.
    Provides category filter tabs, typo tolerance suggestions, and clean empty states.
    """

    template_name = "search/search_results.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        raw_query = self.request.GET.get("q", "")
        selected_category = self.request.GET.get("category", "all").strip().lower()

        cleaned_query = " ".join(raw_query.replace("+", " ").split())
        context["query_string"] = cleaned_query
        context["selected_category"] = selected_category
        context["popular_searches"] = POPULAR_SEARCHES

        if not cleaned_query:
            context["ant_species"] = AntSpecies.objects.none()
            context["journal_entries"] = ColonyJournalEntry.objects.none()
            context["food_items"] = FoodItem.objects.none()
            context["regions"] = AntRegion.objects.none()
            context["species_count"] = 0
            context["journal_count"] = 0
            context["food_count"] = 0
            context["region_count"] = 0
            context["total_results"] = 0
            context["did_you_mean"] = None
            return context

        # 1. Ant Species Search (exact phrase OR multi-token match across taxonomy)
        tokens = cleaned_query.split()
        if len(tokens) > 1:
            token_q = Q()
            for token in tokens:
                token_q &= (
                    Q(name__icontains=token)
                    | Q(commonname__name__icontains=token)
                    | Q(genus__name__icontains=token)
                    | Q(invalid_names__name__icontains=token)
                )
            species_qs = (
                AntSpecies.objects.filter(valid=True)
                .filter(token_q)
                .exclude(name__endswith="sp.")
                .select_related("genus", "genus__tribe", "genus__tribe__sub_family")
                .prefetch_related("images", "sizes", "commonname_set")
                .distinct()
            )
        else:
            species_qs = (
                AntSpecies.objects.search_by_name(cleaned_query)
                .select_related("genus", "genus__tribe", "genus__tribe__sub_family")
                .prefetch_related("images", "sizes", "commonname_set")
            )

        # 2. Colony Journal Entries Search (public colonies only)
        journal_qs = (
            ColonyJournalEntry.objects.filter(
                colony__is_public=True, colony__force_private_by_staff=False
            )
            .filter(
                Q(note__icontains=cleaned_query)
                | Q(colony__name__icontains=cleaned_query)
                | Q(colony__species__name__icontains=cleaned_query)
            )
            .select_related("colony", "colony__user", "colony__species", "colony__title_image")
            .prefetch_related("images", "likes", "comments")
            .order_by("-date", "-created_at")
            .distinct()
        )

        # 3. Food Items Search
        food_qs = (
            FoodItem.objects.filter(
                Q(name__icontains=cleaned_query)
                | Q(description__icontains=cleaned_query)
                | Q(category__icontains=cleaned_query)
            )
            .select_related("created_by")
            .order_by("category", "name")
            .distinct()
        )

        # 4. Regions Search
        regions_qs = (
            AntRegion.objects.filter(
                Q(distribution__isnull=False),
                Q(code__icontains=cleaned_query)
                | Q(name__icontains=cleaned_query)
                | Q(official_name__icontains=cleaned_query)
                | Q(antwiki_name__icontains=cleaned_query),
            )
            .order_by("name")
            .distinct()
        )

        species_count = species_qs.count()
        journal_count = journal_qs.count()
        food_count = food_qs.count()
        region_count = regions_qs.count()
        total_results = species_count + journal_count + food_count + region_count

        context["ant_species"] = species_qs
        context["journal_entries"] = journal_qs
        context["food_items"] = food_qs
        context["regions"] = regions_qs

        context["species_count"] = species_count
        context["journal_count"] = journal_count
        context["food_count"] = food_count
        context["region_count"] = region_count
        context["total_results"] = total_results

        # Typo tolerance suggestion if zero results
        if total_results == 0:
            context["did_you_mean"] = _find_did_you_mean(cleaned_query)
        else:
            context["did_you_mean"] = None

        return context


class SearchAutocompleteView(View):
    """
    Fast JSON autocomplete endpoint for live suggestions in the navbar search bar.
    Returns categorized suggestions (species, journals, food, regions).
    """

    def get(self, request):
        query = request.GET.get("q", "").strip()
        if len(query) < 2:
            return JsonResponse({"results": [], "total": 0})

        # Species suggestions (max 5)
        species = (
            AntSpecies.objects.search_by_name(query)
            .select_related("genus")
            .prefetch_related("commonname_set")[:5]
        )
        species_list = [
            {
                "type": "species",
                "title": s.name,
                "subtitle": s.common_names_str if s.common_names.exists() else (s.genus.name if s.genus else ""),
                "url": s.get_absolute_url(),
                "icon": "bi-bug",
            }
            for s in species
        ]

        # Food suggestions (max 3)
        food_items = FoodItem.objects.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )[:3]
        food_list = [
            {
                "type": "food",
                "title": f.name,
                "subtitle": f.get_category_display(),
                "url": f.get_absolute_url(),
                "icon": "bi-egg-fried",
            }
            for f in food_items
        ]

        # Journal suggestions (max 2)
        journals = (
            ColonyJournalEntry.objects.filter(
                colony__is_public=True, colony__force_private_by_staff=False
            )
            .filter(
                Q(note__icontains=query)
                | Q(colony__name__icontains=query)
                | Q(colony__species__name__icontains=query)
            )
            .select_related("colony", "colony__user")[:2]
        )
        journal_list = [
            {
                "type": "journal",
                "title": f"{j.colony.name} ({j.date})",
                "subtitle": f"@{j.colony.user.username} · {j.get_event_type_display()}",
                "url": j.get_absolute_url(),
                "icon": "bi-journal-bookmark",
            }
            for j in journals
        ]

        # Region suggestions (max 3)
        regions = (
            AntRegion.objects.filter(
                Q(distribution__isnull=False),
                Q(code__icontains=query) | Q(name__icontains=query),
            )[:3]
        )
        region_list = [
            {
                "type": "region",
                "title": r.name,
                "subtitle": r.code or "",
                "url": r.get_absolute_url(),
                "icon": "bi-globe",
            }
            for r in regions
        ]

        total = len(species_list) + len(food_list) + len(journal_list) + len(region_list)

        return JsonResponse({
            "query": query,
            "species": species_list,
            "food": food_list,
            "journals": journal_list,
            "regions": region_list,
            "total": total,
        })
