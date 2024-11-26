"""
URL configuration for config project.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

from main import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.home, name="home"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("register/", views.register, name="register"),
    path("profile/", views.profile, name="profile"),
    # Redirect /accounts/profile/ to /profile/
    path("accounts/profile/", RedirectView.as_view(url="/profile/", permanent=True)),
    path("accounts/logout/", views.logout_view, name="auth_logout"),  # Override default auth logout
    path(
        "accounts/",
        include(
            [
                path("login/", views.login_view, name="auth_login"),
                path("password_change/", include("django.contrib.auth.urls")),
                path("password_change/done/", include("django.contrib.auth.urls")),
                path("password_reset/", include("django.contrib.auth.urls")),
                path("password_reset/done/", include("django.contrib.auth.urls")),
                path("reset/<uidb64>/<token>/", include("django.contrib.auth.urls")),
                path("reset/done/", include("django.contrib.auth.urls")),
            ]
        ),
    ),
    path("image_llama/", views.image_llama, name="image_llama"),
    path("image_open/", views.image_open, name="image_open"),
    path("image_groq/", views.image_groq, name="image_groq"),
    path("doc_classic/", views.process_doc_classic, name="process_doc_classic"),
    path("doc_batches/", views.view_document_batches, name="doc_batches"),
    path("semantic_search/", views.semantic_search, name="semantic_search"),
    path("doc_batch/<str:batch_id>/", views.view_batch_details, name="view_batch_details"),
    path("doc_batch/<str:batch_id>/delete/", views.delete_batch, name="delete_batch"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += [
        path("__debug__/", include("debug_toolbar.urls")),
    ] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
