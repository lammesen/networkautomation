# Generated migration for WebAuthn credential model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0002_add_2fa_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="WebAuthnCredential",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        help_text="User-friendly name for this security key", max_length=100
                    ),
                ),
                (
                    "credential_id",
                    models.BinaryField(help_text="WebAuthn credential ID", unique=True),
                ),
                ("public_key", models.BinaryField(help_text="Public key for this credential")),
                (
                    "sign_count",
                    models.PositiveIntegerField(default=0, help_text="Signature counter"),
                ),
                ("aaguid", models.BinaryField(help_text="Authenticator AAGUID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("last_used_at", models.DateTimeField(blank=True, null=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="webauthn_credentials",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "WebAuthn Credential",
                "verbose_name_plural": "WebAuthn Credentials",
                "indexes": [
                    models.Index(fields=["user"], name="users_webau_user_id_idx"),
                    models.Index(fields=["credential_id"], name="users_webau_credent_idx"),
                ],
            },
        ),
    ]
