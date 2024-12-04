"""
URL configuration for config project.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
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
    path("batch_chapters/", views.view_batch_chapters, name="batch_chapters"),
    path("semantic_search/", views.semantic_search, name="semantic_search"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    import debug_toolbar

    debug_patterns = [path("__debug__/", include(debug_toolbar.urls))]
    admin_patterns = [path("admin/", admin.site.urls)]
    static_patterns = static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns = debug_patterns + admin_patterns + urlpatterns + static_patterns
