# Generated by Django 5.1.1 on 2024-11-21 21:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0005_productreview'),
    ]

    operations = [
        migrations.AlterField(
            model_name='productreview',
            name='comment',
            field=models.TextField(),
        ),
    ]