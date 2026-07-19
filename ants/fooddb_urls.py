from django.urls import path

from . import views

urlpatterns = [
    path("", views.FoodOverviewView.as_view(), name="food_overview"),
    path(
        "rate/",
        views.SubmitFoodRatingFromOverviewView.as_view(),
        name="food_overview_rate",
    ),
    path(
        "rate/<int:pk>/edit/",
        views.FoodRatingSubmissionEditView.as_view(),
        name="food_rating_edit",
    ),
    path(
        "new-item-form/",
        views.FoodOverviewNewItemFormView.as_view(),
        name="food_overview_new_item_form",
    ),
    path(
        "new-item/",
        views.FoodOverviewCreateItemView.as_view(),
        name="food_overview_new_item",
    ),
    path(
        "suggest-similar/",
        views.FoodOverviewSuggestSimilarView.as_view(),
        name="food_overview_suggest_similar",
    ),
    path(
        "<int:food_item_id>/<slug:species_slug>/ratings/",
        views.FoodItemSpeciesRatingsView.as_view(),
        name="food_item_species_ratings",
    ),
    path(
        "<int:food_item_id>/<slug:species_slug>/ratings/list/",
        views.FoodItemSpeciesRatingsListView.as_view(),
        name="food_item_species_ratings_list",
    ),
]
