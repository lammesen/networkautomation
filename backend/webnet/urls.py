"""Project URL configuration."""

from django.contrib import admin
from django.urls import path, include
from webnet.core.metrics import metrics_view
from webnet.users.two_factor_views import (
    CustomLoginView,
    TwoFactorVerifyView,
    TwoFactorSetupView,
    TwoFactorQRCodeView,
    TwoFactorManageView,
    TwoFactorDisableView,
    TwoFactorRegenerateCodesView,
    TwoFactorAdminResetView,
)


from webnet.ui import views as ui_views

urlpatterns = [
    path("metrics/", metrics_view, name="metrics"),
    path("admin/", admin.site.urls),
    path("login/", CustomLoginView.as_view(), name="login"),
    path("logout/", ui_views.logout_view, name="logout"),
    # 2FA URLs
    path("2fa/verify/", TwoFactorVerifyView.as_view(), name="2fa-verify"),
    path("2fa/setup/", TwoFactorSetupView.as_view(), name="2fa-setup"),
    path("2fa/qrcode/", TwoFactorQRCodeView.as_view(), name="2fa-qrcode"),
    path("2fa/manage/", TwoFactorManageView.as_view(), name="2fa-manage"),
    path("2fa/disable/", TwoFactorDisableView.as_view(), name="2fa-disable"),
    path("2fa/regenerate-codes/", TwoFactorRegenerateCodesView.as_view(), name="2fa-regenerate-codes"),
    path("2fa/admin/reset/<int:user_id>/", TwoFactorAdminResetView.as_view(), name="2fa-admin-reset"),
    path("api/v1/", include("webnet.api.urls")),
    path("", include("webnet.ui.urls")),
]
