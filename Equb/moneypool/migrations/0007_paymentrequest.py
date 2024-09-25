# Generated by Django 5.0.4 on 2024-06-23 18:19

import django.db.models.deletion
import django.utils.timezone
import moneypool.models
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('moneypool', '0006_alter_user_bank_account_paymentconfirmation'),
    ]

    operations = [
        migrations.CreateModel(
            name='PaymentRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('creation_date', models.DateTimeField(default=django.utils.timezone.now)),
                ('is_accepted', models.BooleanField(default=False)),
                ('is_expired', models.BooleanField(default=False)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=13)),
                ('round', models.IntegerField(default=1)),
                ('equb', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='%(class)ss', to='moneypool.equb')),
                ('receiver', models.ForeignKey(on_delete=models.SET(moneypool.models.deleted_user), related_name='received_%(class)ss', to=settings.AUTH_USER_MODEL)),
                ('sender', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sent_%(class)ss', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-creation_date'],
                'abstract': False,
            },
        ),
    ]