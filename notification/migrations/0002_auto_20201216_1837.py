# Generated by Django 3.1.3 on 2020-12-16 13:07

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notification', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notification',
            name='timestamp',
            field=models.DateTimeField(default=datetime.datetime(2020, 12, 16, 18, 37, 26, 918469)),
        ),
    ]
