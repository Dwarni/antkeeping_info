from django.urls import path

from . import views

urlpatterns = [
    path('ant-<str:taxonomic_rank>-by-region',
         views.TaxonomicRanksByRegion.as_view(),
         name='taxonomic_ranks_by_region'),
]
