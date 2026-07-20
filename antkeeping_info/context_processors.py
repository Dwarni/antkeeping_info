from django.conf import settings


def discord_url(request):
    return {"discord_url": settings.DISCORD_URL}


def turnstile_site_key(request):
    return {"turnstile_site_key": settings.TURNSTILE_SITE_KEY}
