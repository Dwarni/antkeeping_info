# Generated by Django 2.0.4 on 2018-04-03 19:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ants', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='distribution',
            name='native',
            field=models.NullBooleanField(verbose_name='Native'),
        ),
    ]