from django.urls import path
from django.views.generic import RedirectView

from . import views

urlpatterns = [
    path(
        "ant-<str:taxonomic_rank>-by-region",
        views.TaxonomicRanksByRegion.as_view(),
        name="taxonomic_ranks_by_region",
    ),
    path(
        "top-lists",
        views.TopListsHub.as_view(),
        name="antdb_top_lists",
    ),
    path(
        "food-overview",
        views.FoodOverviewView.as_view(),
        name="food_overview",
    ),
    path(
        "food-overview/rate/",
        views.SubmitFoodRatingFromOverviewView.as_view(),
        name="food_overview_rate",
    ),
    path(
        "food-overview/rate/<int:pk>/edit/",
        views.FoodRatingSubmissionEditView.as_view(),
        name="food_rating_edit",
    ),
    path(
        "food-overview/new-item-form/",
        views.FoodOverviewNewItemFormView.as_view(),
        name="food_overview_new_item_form",
    ),
    path(
        "food-overview/new-item/",
        views.FoodOverviewCreateItemView.as_view(),
        name="food_overview_new_item",
    ),
    path(
        "food-overview/suggest-similar/",
        views.FoodOverviewSuggestSimilarView.as_view(),
        name="food_overview_suggest_similar",
    ),
    path(
        "food-overview/<int:food_item_id>/<slug:species_slug>/ratings/",
        views.FoodItemSpeciesRatingsView.as_view(),
        name="food_item_species_ratings",
    ),
    path(
        "food-overview/<int:food_item_id>/<slug:species_slug>/ratings/list/",
        views.FoodItemSpeciesRatingsListView.as_view(),
        name="food_item_species_ratings_list",
    ),
    path(
        "top-countries-by-number-of-ant-species",
        RedirectView.as_view(
            url="/antdb/top-lists?ranking=countries-by-species", permanent=True
        ),
        name="top_countries_ant_species",
    ),
    path(
        "top-countries-by-number-of-ant-genera",
        RedirectView.as_view(
            url="/antdb/top-lists?ranking=countries-by-genera", permanent=True
        ),
        name="top_countries_ant_genera",
    ),
    path(
        "top-ant-species-by-number-of-countries",
        RedirectView.as_view(
            url="/antdb/top-lists?ranking=species-by-countries", permanent=True
        ),
        name="top_ant_species_countries",
    ),
    path(
        "top-ant-genera-by-number-of-countries",
        RedirectView.as_view(
            url="/antdb/top-lists?ranking=genera-by-countries", permanent=True
        ),
        name="top_ant_genera_countries",
    ),
    path(
        "top-ant-genera-by-number-of-species",
        RedirectView.as_view(
            url="/antdb/top-lists?ranking=genera-by-species", permanent=True
        ),
        name="top_ant_genera_species",
    ),
    path(
        "top-authors-by-number-of-species",
        RedirectView.as_view(
            url="/antdb/top-lists?ranking=authors-by-species", permanent=True
        ),
        name="top_authors_ant_species",
    ),
]
