from django.conf import settings


def discord_url(request):
    return {"discord_url": settings.DISCORD_URL}
