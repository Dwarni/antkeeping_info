from django.db import migrations


def wipe_food_ratings(apps, schema_editor):
    FoodRatingSubmission = apps.get_model("ants", "FoodRatingSubmission")
    # Cascades to RatingPhoto and SpeciesFoodRating.
    FoodRatingSubmission.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('ants', '0062_alter_fooditem_image_author_and_more'),
    ]

    operations = [
        migrations.RunPython(wipe_food_ratings, migrations.RunPython.noop),
    ]
