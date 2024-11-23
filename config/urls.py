"""
URL configuration for config project.
"""
from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from main.views import (
    home, login_view, logout_view,
    register, profile, image_llama, image_open,
    image_groq
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('register/', register, name='register'),
    path('profile/', profile, name='profile'),
    path('accounts/', include('django.contrib.auth.urls')),  # For password reset, etc.
    path('image_llama/', image_llama, name='image_llama'),
    path('image_open/', image_open, name='image_open'),
    path('image_groq/', image_groq, name='image_groq'),
]

if settings.DEBUG:
    urlpatterns += [
        path('__debug__/', include('debug_toolbar.urls')),
    ]