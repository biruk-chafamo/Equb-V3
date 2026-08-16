"""Indexes matching the query shapes, plus the uniqueness the code already assumes."""
from django.db import migrations, models
import django.db.models.functions.text


def _drop_duplicates(model, fields):
    """Delete all but the lowest-id row of each duplicate group."""
    from django.db.models import Count, Min

    duplicated = (
        model.objects.values(*fields)
        .annotate(keep=Min('id'), total=Count('id'))
        .filter(total__gt=1)
    )
    for group in duplicated:
        lookup = {f: group[f] for f in fields}
        model.objects.filter(**lookup).exclude(id=group['keep']).delete()


def dedupe_equb_membership(apps, schema_editor):
    _drop_duplicates(apps.get_model('moneypool', 'EqubMembership'), ['equb', 'member'])


def dedupe_friendship(apps, schema_editor):
    _drop_duplicates(apps.get_model('moneypool', 'Friendship'), ['user', 'friend'])


def dedupe_highest_bid(apps, schema_editor):
    _drop_duplicates(apps.get_model('moneypool', 'HighestBid'), ['equb', 'round'])


class Migration(migrations.Migration):

    dependencies = [
        ('moneypool', '0045_user_google_id'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='bid',
            index=models.Index(fields=['equb', 'round'], name='moneypool_b_equb_id_701158_idx'),
        ),
        migrations.AddIndex(
            model_name='equb',
            index=models.Index(fields=['creation_date'], name='moneypool_e_creatio_dc5618_idx'),
        ),
        migrations.AddIndex(
            model_name='paymentconfirmationrequest',
            index=models.Index(fields=['equb', 'round'], name='moneypool_p_equb_id_8dd985_idx'),
        ),
        migrations.AddIndex(
            model_name='user',
            index=models.Index(fields=['email'], name='moneypool_u_email_b3e680_idx'),
        ),
        migrations.AddIndex(
            model_name='user',
            index=models.Index(django.db.models.functions.text.Upper('email'), name='user_email_upper_idx'),
        ),
        migrations.AddIndex(
            model_name='win',
            index=models.Index(fields=['round'], name='moneypool_w_round_40fdc9_idx'),
        ),
        migrations.RunPython(dedupe_equb_membership, migrations.RunPython.noop, elidable=True),
        migrations.AddConstraint(
            model_name='equbmembership',
            constraint=models.UniqueConstraint(fields=('equb', 'member'), name='unique_equb_member'),
        ),
        migrations.RunPython(dedupe_friendship, migrations.RunPython.noop, elidable=True),
        migrations.AddConstraint(
            model_name='friendship',
            constraint=models.UniqueConstraint(fields=('user', 'friend'), name='unique_friendship'),
        ),
        migrations.RunPython(dedupe_highest_bid, migrations.RunPython.noop, elidable=True),
        migrations.AddConstraint(
            model_name='highestbid',
            constraint=models.UniqueConstraint(fields=('equb', 'round'), name='unique_equb_round_highest_bid'),
        ),
    ]
