"""
url module for ants app
"""

from django.urls import path, register_converter

from . import converters, views

register_converter(converters.CaseInsensitiveSlugConverter, "islug")

urlpatterns = [
    path(
        "nuptial-flight-table/",
        views.NuptialFlightTableView.as_view(),
        name="nuptial_flight_table",
    ),
    path(
        "nuptial-flight-table/rows/",
        views.NuptialFlightTableRowsView.as_view(),
        name="nuptial_flight_table_rows",
    ),
    path(
        "nuptial-flight-table/states/",
        views.NuptialFlightTableStatesView.as_view(),
        name="nuptial_flight_table_states",
    ),
    path(
        "nuptial-flight-table/export/csv/",
        views.NuptialFlightCSVExportView.as_view(),
        name="nuptial_flight_table_csv",
    ),
    path(
        "nuptial-flight-table/export/json/",
        views.NuptialFlightJSONExportView.as_view(),
        name="nuptial_flight_table_json",
    ),
    path(
        "keeping-forbidden-in-eu-species/",
        views.ForbiddenInEUSpeciesListView.as_view(),
        name="forbidden_in_eu_species_list",
    ),
    path(
        "ant-species-autocomplete/",
        views.AntSpeciesAutocomplete.as_view(),
        name="ant_species_autocomplete",
    ),
    path(
        "nuptial-flight-table/report/",
        views.NuptialFlightReportView.as_view(),
        name="nuptial_flight_report",
    ),
    path(
        "nuptial-flight-table/species-suggest/",
        views.NuptialFlightSpeciesSuggestView.as_view(),
        name="nuptial_flight_species_suggest",
    ),
    path(
        "species/filter/",
        views.SpeciesFilterView.as_view(),
        name="species_filter",
    ),
    path(
        "species/filter/results/",
        views.SpeciesFilterResultsView.as_view(),
        name="species_filter_results",
    ),
    path("<islug:slug>/", views.AntSpeciesDetail.as_view(), name="ant_detail"),
]
