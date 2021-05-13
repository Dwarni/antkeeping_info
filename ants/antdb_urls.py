from django.urls import path

from . import views

urlpatterns = [
    path('ant-<str:taxonomic_rank>-by-region',
         views.TaxonomicRanksByRegion.as_view(),
         name='taxonomic_ranks_by_region'),
    path('top-countries-by-number-of-ant-species',
         views.TopCountriesByNumberOfAntSpecies.as_view(),
         name='top_countries_ant_species'),
    path('top-countries-by-number-of-ant-genera',
         views.TopCountriesByNumberOfAntGenera.as_view(),
         name='top_countries_ant_genera'),
    path('top-ant-species-by-number-of-countries',
         views.TopAntSpeciesByNumberOfCountries.as_view(),
         name='top_ant_species_countries'),
    path('top-ant-genera-by-number-of-countries',
         views.TopAntGeneraByNumberOfCountries.as_view(),
         name='top_ant_genera_countries'),
    path('top-ant-genera-by-number-of-species',
         views.TopAntGeneraByNumberOfSpecies.as_view(),
         name='top_ant_genera_species'),
    path('top-authors-by-number-of-species',
         views.TopAuthorsByNumberOfAntSpecies.as_view(),
         name='top_authors_ant_species'),
]
