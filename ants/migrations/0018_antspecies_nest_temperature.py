# Generated by Django 2.2.2 on 2019-06-15 03:22

import django.contrib.postgres.fields.ranges
import django.core.validators
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ants', '0017_auto_20190611_2024'),
    ]

    operations = [
        migrations.AddField(
            model_name='antspecies',
            name='nest_temperature',
            field=django.contrib.postgres.fields.ranges.IntegerRangeField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(40)], verbose_name='Nest temperature'),
        ),
    ]