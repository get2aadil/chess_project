# Generated by Django 5.1.1 on 2024-10-07 20:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('game', '0003_challenge'),
    ]

    operations = [
        migrations.AddField(
            model_name='challenge',
            name='challenger_notified',
            field=models.BooleanField(default=False),
        ),
    ]
