# Generated by Django 2.0.6 on 2018-06-26 10:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('flights', '0026_auto_20180611_2158'),
    ]

    operations = [
        migrations.AddField(
            model_name='flight',
            name='location_type',
            field=models.CharField(choices=[('LATLNG', 'Latitude/Longitude'), ('ADDR', 'Address')], default='ADDR', max_length=6),
            preserve_default=False,
        ),
    ]
