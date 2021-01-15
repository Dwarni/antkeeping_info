"""antkeeping_info URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

from wagtail.admin import urls as wagtailadmin_urls
from wagtail.documents import urls as wagtaildocs_urls
from wagtail.core import urls as wagtail_urls

from home import views
from search import views as search_views

urlpatterns = [
    path('', views.home, name="home"),
    path('ants/', include('ants.urls')),
    path('ants-by-country/', include('ants.ants_by_country_urls')),
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
    path('cms/', include(wagtailadmin_urls)),
    path('documents/', include(wagtaildocs_urls)),
    path('pages/', include(wagtail_urls)),

]

""" urlpatterns += i18n_patterns(
    # These URLs will have /<language_code>/ appended to the beginning

    path('', include(wagtail_urls)),
) """

admin.site.site_header = 'Antkeeping.info administration'

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT)
