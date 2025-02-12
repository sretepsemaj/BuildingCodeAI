"""
URL configuration for config project.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from main import views

urlpatterns = [
    path("", views.home, name="home"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("register/", views.register, name="register"),
    path("profile/", views.profile, name="profile"),
    path("process/", views.process_upload, name="process_upload"),
    path("process/start/", views.start_processing, name="start_processing"),
    path("process/cleanup/", views.cleanup_intermediate_dirs, name="cleanup_intermediate_dirs"),
    path("process-plumbing/", views.process_plumbing_data, name="process_plumbing"),
    path("batch_chapters/", views.view_batch_chapters, name="batch_chapters"),
    path("semantic_search/", views.semantic_search, name="semantic_search"),
    # Password reset URLs
    path("password_reset/", auth_views.PasswordResetView.as_view(), name="password_reset"),
    path(
        "password_reset/done/",
        auth_views.PasswordResetDoneView.as_view(),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(),
        name="password_reset_complete",
    ),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    import debug_toolbar

    debug_patterns = [path("__debug__/", include(debug_toolbar.urls))]
    admin_patterns = [path("admin/", admin.site.urls)]
    static_patterns = static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns = debug_patterns + admin_patterns + urlpatterns + static_patterns
