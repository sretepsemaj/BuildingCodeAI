"""
URL configuration for config project.
"""
from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from main import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register, name='register'),
    path('profile/', views.profile, name='profile'),
    path('accounts/', include('django.contrib.auth.urls')),  # For password reset, etc.
    path('image_llama/', views.image_llama, name='image_llama'),
    path('image_open/', views.image_open, name='image_open'),
    path('image_groq/', views.image_groq, name='image_groq'),
    path('doc_classic/', views.process_doc_classic, name='process_doc_classic'),
    path('doc_batches/', views.view_document_batches, name='view_document_batches'),
    path('doc_batch/<str:batch_id>/', views.view_batch_details, name='view_batch_details'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += [
        path('__debug__/', include('debug_toolbar.urls')),
    ] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)