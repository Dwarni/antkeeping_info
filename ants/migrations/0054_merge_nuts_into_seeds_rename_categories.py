from django.db import migrations, models


def merge_nuts_into_seeds(apps, schema_editor):
    FoodItem = apps.get_model("ants", "FoodItem")
    FoodItem.objects.filter(category="NUTS").update(category="SEEDS")


class Migration(migrations.Migration):

    dependencies = [
        ("ants", "0053_expand_food_rating_5stars"),
    ]

    operations = [
        migrations.RunPython(merge_nuts_into_seeds, reverse_code=migrations.RunPython.noop),
        migrations.AlterField(
            model_name="fooditem",
            name="category",
            field=models.CharField(
                max_length=20,
                choices=[
                    ("PROTEIN", "Protein"),
                    ("SUGAR", "Carbohydrates"),
                    ("SEEDS", "Seeds"),
                    ("PLANT", "Leaves"),
                    ("OTHER", "Other"),
                ],
            ),
        ),
    ]
