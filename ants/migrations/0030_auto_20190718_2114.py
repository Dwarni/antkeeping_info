# Generated by Django 2.2.3 on 2019-07-18 21:14

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('ants', '0029_auto_20190718_1951'),
    ]

    operations = [
        migrations.AddField(
            model_name='antspecies',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AddField(
            model_name='antspecies',
            name='created_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_ant_species', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='antspecies',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, null=True),
        ),
        migrations.AddField(
            model_name='antspecies',
            name='updated_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='updated_ant_species', to=settings.AUTH_USER_MODEL),
        ),
    ]