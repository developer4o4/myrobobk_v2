# Generated migration for payment app

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PaymeTransaction',
            fields=[
                ('id', models.CharField(editable=False, max_length=36, primary_key=True, serialize=False, unique=True)),
                ('provider', models.CharField(choices=[('payme', 'Payme')], default='payme', max_length=20)),
                ('payme_transaction_id', models.CharField(blank=True, db_index=True, max_length=64, null=True, unique=True)),
                ('amount_tiyin', models.PositiveBigIntegerField()),
                ('state', models.SmallIntegerField(choices=[(1, 'Pending'), (2, 'Done'), (-1, 'Canceled')], db_index=True, default=1)),
                ('create_time', models.BigIntegerField(default=0)),
                ('perform_time', models.BigIntegerField(blank=True, null=True)),
                ('cancel_time', models.BigIntegerField(blank=True, null=True)),
                ('reason', models.IntegerField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payme_transactions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'payme_transactions',
                'ordering': ('-created_at',),
            },
        ),
        migrations.AddIndex(
            model_name='paymetransaction',
            index=models.Index(fields=['user', '-created_at'], name='payme_trans_user_id_created_idx'),
        ),
        migrations.AddIndex(
            model_name='paymetransaction',
            index=models.Index(fields=['payme_transaction_id'], name='payme_trans_payme_tra_idx'),
        ),
        migrations.AddIndex(
            model_name='paymetransaction',
            index=models.Index(fields=['state'], name='payme_trans_state_idx'),
        ),
    ]
