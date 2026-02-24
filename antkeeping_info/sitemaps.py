from django.contrib.sitemaps import Sitemap

from ants.models import AntSpecies


class AntSpeciesSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return AntSpecies.objects.all()

    def lastmod(self, obj):
        return getattr(obj, "updated_at", None)
