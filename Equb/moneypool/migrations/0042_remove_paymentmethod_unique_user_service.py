# Generated by Django 5.0.4 on 2024-09-08 00:04

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('moneypool', '0041_rename_username_paymentmethod_detail'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='paymentmethod',
            name='unique_user_service',
        ),
    ]
