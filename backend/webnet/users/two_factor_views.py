"""Two-factor authentication views."""

from __future__ import annotations

import io
from typing import Any

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View
from django_otp import match_token
from django_otp.decorators import otp_required

import qrcode

from webnet.users.models import User
from webnet.users.two_factor_service import TwoFactorService


class CustomLoginView(DjangoLoginView):
    """Custom login view that handles 2FA verification."""

    template_name = "auth/login.html"

    def form_valid(self, form: Any) -> HttpResponse:
        """Process valid login form and redirect to 2FA verification if needed."""
        user = form.get_user()
        
        # Check if user has 2FA enabled
        if user.is_2fa_enabled():
            # Store user ID in session for 2FA verification
            self.request.session["2fa_user_id"] = user.id
            self.request.session["2fa_backend"] = user.backend
            return redirect("2fa-verify")
        
        # No 2FA required, proceed with normal login
        login(self.request, user)
        
        # Check if 2FA is required but not enabled
        if user.two_factor_required and not user.two_factor_enabled:
            messages.warning(
                self.request,
                "Two-factor authentication is required for your account. Please set it up now."
            )
            return redirect("2fa-setup")
        
        return super().form_valid(form)


class TwoFactorVerifyView(View):
    """View for verifying 2FA token during login."""

    template_name = "auth/2fa_verify.html"

    def get(self, request: Any) -> HttpResponse:
        """Display 2FA verification form."""
        user_id = request.session.get("2fa_user_id")
        if not user_id:
            return redirect("login")
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return redirect("login")
        
        context = {
            "username": user.username,
            "has_backup_codes": user.has_backup_codes(),
        }
        return render(request, self.template_name, context)

    def post(self, request: Any) -> HttpResponse:
        """Process 2FA token submission."""
        user_id = request.session.get("2fa_user_id")
        backend = request.session.get("2fa_backend")
        
        if not user_id:
            return redirect("login")
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return redirect("login")
        
        token = request.POST.get("token", "").strip()
        use_backup = request.POST.get("use_backup") == "true"
        
        valid = False
        
        if use_backup:
            # Verify backup code
            valid = TwoFactorService.verify_backup_code(user, token)
            if valid:
                messages.info(
                    request,
                    "Backup code used successfully. Consider regenerating your backup codes."
                )
        else:
            # Verify TOTP token
            valid = TwoFactorService.verify_totp_token(user, token)
        
        if valid:
            # Clear 2FA session data
            del request.session["2fa_user_id"]
            if "2fa_backend" in request.session:
                del request.session["2fa_backend"]
            
            # Log user in
            user.backend = backend
            login(request, user)
            
            return redirect(request.GET.get("next", "/"))
        
        # Invalid token
        context = {
            "username": user.username,
            "has_backup_codes": user.has_backup_codes(),
            "error": "Invalid verification code. Please try again.",
        }
        return render(request, self.template_name, context)


class TwoFactorSetupView(LoginRequiredMixin, View):
    """View for setting up 2FA."""

    template_name = "auth/2fa_setup.html"

    def get(self, request: Any) -> HttpResponse:
        """Display 2FA setup page."""
        user = request.user
        
        # Create or get unconfirmed TOTP device
        device = TwoFactorService.enable_totp_for_user(user)
        
        # Generate QR code URL
        qr_url = device.config_url
        
        context = {
            "qr_url": qr_url,
            "secret": device.key,
        }
        return render(request, self.template_name, context)

    def post(self, request: Any) -> HttpResponse:
        """Verify and confirm 2FA setup."""
        user = request.user
        token = request.POST.get("token", "").strip()
        
        # Get unconfirmed device
        from django_otp.plugins.otp_totp.models import TOTPDevice
        try:
            device = TOTPDevice.objects.get(user=user, confirmed=False)
        except TOTPDevice.DoesNotExist:
            messages.error(request, "No pending 2FA setup found. Please try again.")
            return redirect("2fa-setup")
        
        # Verify token and confirm device
        if TwoFactorService.confirm_totp_device(device, token):
            # Generate backup codes
            backup_codes = TwoFactorService.regenerate_backup_codes(user)
            
            messages.success(request, "Two-factor authentication has been enabled successfully!")
            
            # Show backup codes
            return render(request, "auth/2fa_backup_codes.html", {
                "backup_codes": backup_codes,
            })
        
        # Invalid token
        qr_url = device.config_url
        context = {
            "qr_url": qr_url,
            "secret": device.key,
            "error": "Invalid verification code. Please try again.",
        }
        return render(request, self.template_name, context)


class TwoFactorQRCodeView(LoginRequiredMixin, View):
    """View for generating QR code image."""

    def get(self, request: Any) -> HttpResponse:
        """Generate and return QR code image."""
        user = request.user
        
        from django_otp.plugins.otp_totp.models import TOTPDevice
        try:
            device = TOTPDevice.objects.get(user=user, confirmed=False)
        except TOTPDevice.DoesNotExist:
            return HttpResponse("No pending setup", status=404)
        
        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(device.config_url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Return image
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        
        return HttpResponse(buffer.getvalue(), content_type="image/png")


class TwoFactorManageView(LoginRequiredMixin, View):
    """View for managing 2FA settings."""

    template_name = "auth/2fa_manage.html"

    def get(self, request: Any) -> HttpResponse:
        """Display 2FA management page."""
        user = request.user
        
        context = {
            "two_factor_enabled": user.two_factor_enabled,
            "two_factor_required": user.two_factor_required,
            "has_backup_codes": user.has_backup_codes(),
            "backup_codes_count": len(user.backup_codes) if user.backup_codes else 0,
        }
        return render(request, self.template_name, context)


class TwoFactorDisableView(LoginRequiredMixin, View):
    """View for disabling 2FA."""

    def post(self, request: Any) -> HttpResponse:
        """Disable 2FA for user."""
        user = request.user
        
        # Check if 2FA is required
        if user.two_factor_required:
            messages.error(request, "Two-factor authentication is required for your account and cannot be disabled.")
            return redirect("2fa-manage")
        
        # Disable 2FA
        TwoFactorService.disable_2fa_for_user(user)
        messages.success(request, "Two-factor authentication has been disabled.")
        
        return redirect("2fa-manage")


class TwoFactorRegenerateCodesView(LoginRequiredMixin, View):
    """View for regenerating backup codes."""

    def post(self, request: Any) -> HttpResponse:
        """Regenerate backup codes."""
        user = request.user
        
        if not user.two_factor_enabled:
            messages.error(request, "Two-factor authentication must be enabled first.")
            return redirect("2fa-manage")
        
        # Regenerate codes
        backup_codes = TwoFactorService.regenerate_backup_codes(user)
        
        messages.success(request, "New backup codes have been generated.")
        
        return render(request, "auth/2fa_backup_codes.html", {
            "backup_codes": backup_codes,
            "regenerated": True,
        })


class TwoFactorAdminResetView(LoginRequiredMixin, View):
    """View for admins to reset user's 2FA."""

    def post(self, request: Any, user_id: int) -> HttpResponse:
        """Reset 2FA for a user (admin only)."""
        # Check if current user is admin
        if request.user.role != "admin":
            messages.error(request, "Only administrators can reset 2FA for other users.")
            return redirect("dashboard")
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            messages.error(request, "User not found.")
            return redirect("dashboard")
        
        # Reset 2FA
        TwoFactorService.disable_2fa_for_user(user)
        
        messages.success(request, f"Two-factor authentication has been reset for {user.username}.")
        
        # Redirect to user management or admin
        return redirect("admin:users_user_change", user_id)
