from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.shortcuts import redirect, render
import os
from django.conf import settings
from datetime import datetime

def home(request):
    return render(request, "main/home.html")


def login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f"Welcome back, {username}!")
                return redirect("home")
            else:
                messages.error(request, "Invalid username or password.")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = AuthenticationForm()
    return render(request, "registration/login.html", {"form": form})


def register(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Registration successful!")
            return redirect("home")
        else:
            messages.error(request, "Registration failed. Please correct the errors.")
    else:
        form = UserCreationForm()
    return render(request, "registration/register.html", {"form": form})


@login_required
def profile(request):
    return render(request, "main/profile.html")


@login_required
def image_processor(request):
    from .utils.image_processor import LlamaImageProcessor
    
    try:
        # Initialize the processor
        processor = LlamaImageProcessor()
        
        # Use the static images directory
        png_directory = os.path.join(settings.BASE_DIR, 'main', 'static', 'images')
        
        # Process all PNG files in the directory
        response = processor.process_directory(png_directory)
        
        return render(request, 'main/image_processor.html', {
            'response': response
        })
    except Exception as e:
        return render(request, 'main/image_processor.html', {
            'response': {
                'success': False,
                'message': f'Error processing images: {str(e)}',
                'results': []
            }
        })


def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect("home")
