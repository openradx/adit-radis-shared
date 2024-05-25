# Generated by Django 4.2.11 on 2024-03-26 01:08

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        # ('sites', '0002_alter_domain_unique'),
    ]

    operations = [
        migrations.CreateModel(
            name='SiteProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('meta_keywords', models.TextField(blank=True)),
                ('meta_description', models.TextField(blank=True)),
                ('project_url', models.URLField(blank=True)),
                ('announcement', models.TextField(blank=True)),
                ('maintenance', models.BooleanField(default=False)),
                # ('site', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='profile', to='sites.site')),
            ],
        ),
    ]
