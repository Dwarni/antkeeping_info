# Generated by Django 3.2.2 on 2021-05-12 11:30

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ants', '0041_alter_species_name'),
    ]

    operations = [
        migrations.AlterField(
            model_name='family',
            name='name',
            field=models.CharField(db_index=True, max_length=200, unique=True, validators=[django.core.validators.RegexValidator('^[A-Z][a-z]+$')]),
        ),
        migrations.AlterField(
            model_name='genus',
            name='name',
            field=models.CharField(db_index=True, max_length=200, unique=True, validators=[django.core.validators.RegexValidator('^[A-Z][a-z]+$')]),
        ),
        migrations.AlterField(
            model_name='subfamily',
            name='name',
            field=models.CharField(db_index=True, max_length=200, unique=True, validators=[django.core.validators.RegexValidator('^[A-Z][a-z]+$')]),
        ),
        migrations.AlterField(
            model_name='tribe',
            name='name',
            field=models.CharField(db_index=True, max_length=200, unique=True, validators=[django.core.validators.RegexValidator('^[A-Z][a-z]+$')]),
        ),
    ]
