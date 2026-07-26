from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ants', '0063_wipe_food_ratings'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='speciesfoodrating',
            name='submission',
        ),
        migrations.DeleteModel(
            name='RatingPhoto',
        ),
        migrations.DeleteModel(
            name='FoodRatingSubmission',
        ),
        migrations.AddField(
            model_name='speciesfoodrating',
            name='vote',
            field=models.SmallIntegerField(choices=[(1, 'Accepts it'), (-1, "Doesn't accept it")]),
        ),
    ]
