# Generated by Django 2.0.5 on 2018-05-15 16:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ants', '0007_antspecies_hibernation'),
    ]

    operations = [
        migrations.AlterField(
            model_name='distribution',
            name='red_list_status',
            field=models.TextField(blank=True, choices=[('NOT_ON_RED_LIST', 'Not on red list'), ('LEAST_CONCERN', 'Least Concern'), ('NEAR_THREATENED', 'Near Threatened'), ('VULNERABLE', 'Vulnerable'), ('ENDANGERED', 'Endangered'), ('CRITICALLY_ENDANGERED', 'Critically Endangered'), ('EXTINCT_IN_WILD', 'Extinct in the Wild'), ('EXTINCT', 'Extinct')], max_length=40, null=True),
        ),
    ]