# Generated by Django 2.2.3 on 2019-07-15 22:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ants', '0027_auto_20190714_2035'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='antspecies',
            name='main_image',
        ),
        migrations.AddField(
            model_name='antspeciesimage',
            name='main_image',
            field=models.BooleanField(default=False, verbose_name='Main image'),
        ),
    ]