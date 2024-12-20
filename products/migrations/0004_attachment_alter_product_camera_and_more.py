# Generated by Django 5.1.1 on 2024-11-12 15:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0003_alter_product_price'),
    ]

    operations = [
        migrations.CreateModel(
            name='Attachment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField()),
                ('price', models.DecimalField(decimal_places=2, max_digits=7)),
                ('sku', models.CharField(max_length=50, unique=True)),
                ('image', models.ImageField(blank=True, null=True, upload_to='attachments/')),
            ],
        ),
        migrations.AlterField(
            model_name='product',
            name='camera',
            field=models.CharField(blank=True, choices=[('Yes', 'Yes'), ('No', 'No')], max_length=3, null=True),
        ),
        migrations.AlterField(
            model_name='product',
            name='collision_avoidance',
            field=models.CharField(blank=True, choices=[('Yes', 'Yes'), ('No', 'No')], max_length=3, null=True),
        ),
        migrations.AlterField(
            model_name='product',
            name='gps',
            field=models.CharField(blank=True, choices=[('Yes', 'Yes'), ('No', 'No')], max_length=3, null=True),
        ),
        migrations.AlterField(
            model_name='product',
            name='mobile_app_support',
            field=models.CharField(blank=True, choices=[('Yes', 'Yes'), ('No', 'No')], max_length=3, null=True),
        ),
        migrations.AlterField(
            model_name='product',
            name='remote_control',
            field=models.CharField(blank=True, choices=[('Yes', 'Yes'), ('No', 'No')], max_length=3, null=True),
        ),
        migrations.AlterField(
            model_name='product',
            name='wind_resistance',
            field=models.CharField(blank=True, choices=[('Yes', 'Yes'), ('No', 'No')], max_length=3, null=True),
        ),
    ]
