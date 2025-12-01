"""Project URL configuration."""

from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include
from webnet.core.metrics import metrics_view


from webnet.ui import views as ui_views

urlpatterns = [
    path("metrics/", metrics_view, name="metrics"),
    path("admin/", admin.site.urls),
    path("login/", auth_views.LoginView.as_view(template_name="auth/login.html"), name="login"),
    path("logout/", ui_views.logout_view, name="logout"),
    path("api/v1/", include("webnet.api.urls")),
    path("", include("webnet.ui.urls")),
]
