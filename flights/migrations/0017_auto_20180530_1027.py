# Generated by Django 2.0.5 on 2018-05-30 08:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('flights', '0016_auto_20180530_1018'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='flight',
            name='weather_comment',
        ),
        migrations.AlterField(
            model_name='flight',
            name='spotting_type',
            field=models.CharField(choices=[('F', 'Nuptial Flight'), ('FP', 'Flight preparation'), ('Q', 'Wingless (dealated) queen'), ('QW', 'Winged (alate) queen'), ('M', 'Male')], max_length=2),
        ),
    ]