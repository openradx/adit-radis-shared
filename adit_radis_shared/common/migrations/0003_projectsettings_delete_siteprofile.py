# Generated by Django 5.0.4 on 2024-05-25 19:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0002_update_or_create_site'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProjectSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('announcement', models.TextField(blank=True)),
                ('maintenance', models.BooleanField(default=False)),
            ],
            options={
                'verbose_name_plural': 'Project settings',
            },
        ),
        migrations.DeleteModel(
            name='SiteProfile',
        ),
    ]
