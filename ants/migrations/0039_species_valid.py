# Generated by Django 3.2.2 on 2021-05-11 11:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ants', '0038_auto_20210511_0014'),
    ]

    operations = [
        migrations.AddField(
            model_name='species',
            name='valid',
            field=models.BooleanField(db_index=True, default=True),
        ),
    ]
