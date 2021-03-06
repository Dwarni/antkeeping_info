# Generated by Django 2.0.5 on 2018-05-29 04:44

from django.db import migrations, models
import taggit.managers


class Migration(migrations.Migration):

    dependencies = [
        ('taggit', '0002_auto_20150616_2121'),
        ('flights', '0010_auto_20180527_0131'),
    ]

    operations = [
        migrations.AddField(
            model_name='flight',
            name='habitat',
            field=taggit.managers.TaggableManager(help_text='A comma-separated list of tags.', through='taggit.TaggedItem', to='taggit.Tag', verbose_name='Tags'),
        ),
        migrations.AddField(
            model_name='flight',
            name='weather_comment',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
    ]
