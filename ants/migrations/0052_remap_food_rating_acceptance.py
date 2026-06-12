from django.db import migrations
from django.db.models import F


def remap_forward(apps, schema_editor):
    # Old: LIKED=1, ACCEPTED=2, IGNORED=3
    # New: ONE_STAR=1 (ignored), TWO_STARS=2 (accepted), THREE_STARS=3 (liked)
    # Formula: new = 4 - old  (self-inverse, so reverse is the same)
    SpeciesFoodRating = apps.get_model("ants", "SpeciesFoodRating")
    SpeciesFoodRating.objects.update(acceptance=4 - F("acceptance"))


class Migration(migrations.Migration):

    dependencies = [
        ("ants", "0051_fooditem_speciesfoodrating"),
    ]

    operations = [
        migrations.RunPython(remap_forward, remap_forward),
    ]
