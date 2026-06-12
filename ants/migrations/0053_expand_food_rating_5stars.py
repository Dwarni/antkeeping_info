from django.db import migrations, models


def remap_forward(apps, schema_editor):
    # Old: 1=Ignored, 2=Accepted, 3=Really liked
    # New: 1=Ignored, 3=Moderately interested, 5=Extremely interested
    SpeciesFoodRating = apps.get_model("ants", "SpeciesFoodRating")
    mapping = {1: 1, 2: 3, 3: 5}
    for old, new in mapping.items():
        SpeciesFoodRating.objects.filter(acceptance=old).update(acceptance=new)


def remap_reverse(apps, schema_editor):
    # Reverse: 1→1, 3→2, 5→3 (2 and 4 were not in DB before forward migration)
    SpeciesFoodRating = apps.get_model("ants", "SpeciesFoodRating")
    mapping = {5: 3, 3: 2, 1: 1}
    for old, new in mapping.items():
        SpeciesFoodRating.objects.filter(acceptance=old).update(acceptance=new)


class Migration(migrations.Migration):

    dependencies = [
        ("ants", "0052_remap_food_rating_acceptance"),
    ]

    operations = [
        migrations.AlterField(
            model_name="speciesfoodrating",
            name="acceptance",
            field=models.PositiveSmallIntegerField(
                choices=[
                    (1, "Ignored"),
                    (2, "Hardly interested"),
                    (3, "Moderately interested"),
                    (4, "Above average interest"),
                    (5, "Extremely interested (strong recruitment)"),
                ]
            ),
        ),
        migrations.RunPython(remap_forward, remap_reverse),
    ]
