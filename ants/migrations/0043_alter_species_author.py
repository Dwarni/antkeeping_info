# Generated by Django 3.2.2 on 2021-05-12 11:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ants', '0042_auto_20210512_1130'),
    ]

    operations = [
        migrations.AlterField(
            model_name='species',
            name='author',
            field=models.CharField(blank=True, db_index=True, max_length=300, null=True),
        ),
    ]