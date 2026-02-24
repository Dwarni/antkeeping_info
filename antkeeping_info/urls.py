"""
antkeeping_info URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

if settings.DEBUG:
    from debug_toolbar.toolbar import debug_toolbar_urls

from django.urls import include, path
from django.views.generic import TemplateView

from home import views
from search import views as search_views
from ants import views as ants_views

urlpatterns = [
    path('', views.home, name="home"),
    path('ants/', include('ants.urls')),
    path('antdb/', include('ants.antdb_urls')),
    path('ants-by-country/<str:country>/', ants_views.ants_by_country,
         name='ants_by_country'),
    path('flights/', include('flights.urls')),
    path('search/', search_views.SearchView.as_view(), name='search'),
    path('staff/', include('staff.urls')),
    path('admin/', admin.site.urls),
    path('users/', include('users.urls')),
    path(
        'legal-notice/',
        TemplateView.as_view(template_name='legal_notice.html'),
        name='legal'
    ),
    path(
        'privacy-policy/',
        TemplateView.as_view(template_name='privacy_policy.html'),
        name='privacy'
    ),
    path('api/', include('api.urls')),
    path('tinymce/', include('tinymce.urls')),
]

admin.site.site_header = 'Antkeeping.info administration'

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT)
    urlpatterns += staticfiles_urlpatterns()


if settings.DEBUG and not settings.TESTING:
    urlpatterns = [
        *urlpatterns,
    ] + debug_toolbar_urls()
