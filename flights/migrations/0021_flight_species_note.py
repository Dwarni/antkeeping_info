# Generated by Django 2.0.5 on 2018-05-30 09:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('flights', '0020_auto_20180530_1106'),
    ]

    operations = [
        migrations.AddField(
            model_name='flight',
            name='species_note',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
    ]
