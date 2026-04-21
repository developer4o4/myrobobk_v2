# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='active_session_key',
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
    ]