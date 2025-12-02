# Generated migration for 2FA fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='two_factor_enabled',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='user',
            name='two_factor_required',
            field=models.BooleanField(
                default=False,
                help_text='If True, user must enable 2FA before accessing the system'
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='backup_codes',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='Hashed backup codes for account recovery'
            ),
        ),
    ]
