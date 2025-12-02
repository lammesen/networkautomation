"""WebAuthn/FIDO2 service for hardware token authentication."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.utils import timezone
from webauthn import (
    generate_registration_options,
    verify_registration_response,
    generate_authentication_options,
    verify_authentication_response,
    options_to_json,
)
from webauthn.helpers import bytes_to_base64url, base64url_to_bytes
from webauthn.helpers.structs import (
    PublicKeyCredentialDescriptor,
    AuthenticatorSelectionCriteria,
    UserVerificationRequirement,
    ResidentKeyRequirement,
)

if TYPE_CHECKING:
    from webnet.users.models import User, WebAuthnCredential


class WebAuthnService:
    """Service for managing WebAuthn/FIDO2 credentials."""

    # Get RP ID from settings or default to localhost for development
    RP_ID = getattr(settings, "WEBAUTHN_RP_ID", "localhost")
    RP_NAME = getattr(settings, "WEBAUTHN_RP_NAME", "webnet Network Automation")
    # Origin should match the URL scheme, host, and port
    ORIGIN = getattr(settings, "WEBAUTHN_ORIGIN", "http://localhost:8000")

    @staticmethod
    def start_registration(user: User) -> dict[str, Any]:
        """Start WebAuthn registration process for a user."""
        # Get existing credentials to exclude
        existing_credentials = []
        for cred in user.webauthn_credentials.all():
            existing_credentials.append(
                PublicKeyCredentialDescriptor(
                    id=bytes(cred.credential_id),
                )
            )

        # Generate registration options
        options = generate_registration_options(
            rp_id=WebAuthnService.RP_ID,
            rp_name=WebAuthnService.RP_NAME,
            user_id=str(user.id).encode("utf-8"),
            user_name=user.username,
            user_display_name=user.get_full_name() or user.username,
            exclude_credentials=existing_credentials,
            authenticator_selection=AuthenticatorSelectionCriteria(
                authenticator_attachment=None,  # Support both platform and cross-platform
                resident_key=ResidentKeyRequirement.DISCOURAGED,
                user_verification=UserVerificationRequirement.PREFERRED,
            ),
        )

        # Store challenge in session (will be done by view)
        return {
            "options": json.loads(options_to_json(options)),
            "challenge": bytes_to_base64url(options.challenge),
        }

    @staticmethod
    def verify_registration(
        user: User,
        credential_name: str,
        credential_data: dict[str, Any],
        challenge: str,
    ) -> WebAuthnCredential:
        """Verify registration response and create credential."""
        from webnet.users.models import WebAuthnCredential

        # Verify the registration response
        verification = verify_registration_response(
            credential=credential_data,
            expected_challenge=base64url_to_bytes(challenge),
            expected_origin=WebAuthnService.ORIGIN,
            expected_rp_id=WebAuthnService.RP_ID,
        )

        # Create and save the credential
        credential = WebAuthnCredential.objects.create(
            user=user,
            name=credential_name,
            credential_id=verification.credential_id,
            public_key=verification.credential_public_key,
            sign_count=verification.sign_count,
            aaguid=verification.aaguid,
        )

        return credential

    @staticmethod
    def start_authentication(user: User) -> dict[str, Any]:
        """Start WebAuthn authentication process for a user."""
        # Get user's credentials
        credentials = []
        for cred in user.webauthn_credentials.all():
            credentials.append(
                PublicKeyCredentialDescriptor(
                    id=bytes(cred.credential_id),
                )
            )

        if not credentials:
            raise ValueError("No WebAuthn credentials found for user")

        # Generate authentication options
        options = generate_authentication_options(
            rp_id=WebAuthnService.RP_ID,
            allow_credentials=credentials,
            user_verification=UserVerificationRequirement.PREFERRED,
        )

        return {
            "options": json.loads(options_to_json(options)),
            "challenge": bytes_to_base64url(options.challenge),
        }

    @staticmethod
    def verify_authentication(
        user: User,
        credential_data: dict[str, Any],
        challenge: str,
    ) -> bool:
        """Verify authentication response."""
        from webnet.users.models import WebAuthnCredential

        credential_id = base64url_to_bytes(credential_data["id"])

        # Find the credential
        try:
            credential = WebAuthnCredential.objects.get(
                user=user,
                credential_id=credential_id,
            )
        except WebAuthnCredential.DoesNotExist:
            return False

        # Verify the authentication response
        try:
            verification = verify_authentication_response(
                credential=credential_data,
                expected_challenge=base64url_to_bytes(challenge),
                expected_origin=WebAuthnService.ORIGIN,
                expected_rp_id=WebAuthnService.RP_ID,
                credential_public_key=bytes(credential.public_key),
                credential_current_sign_count=credential.sign_count,
            )

            # Update credential
            credential.sign_count = verification.new_sign_count
            credential.last_used_at = timezone.now()
            credential.save(update_fields=["sign_count", "last_used_at"])

            return True
        except Exception:
            return False

    @staticmethod
    def delete_credential(credential_id: int, user: User) -> None:
        """Delete a WebAuthn credential."""
        from webnet.users.models import WebAuthnCredential

        WebAuthnCredential.objects.filter(id=credential_id, user=user).delete()

    @staticmethod
    def get_user_credentials(user: User) -> list[WebAuthnCredential]:
        """Get all WebAuthn credentials for a user."""
        return list(user.webauthn_credentials.all())
