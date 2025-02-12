"""Views for the main application.

This module contains all the view functions for handling web requests in the main application.
It includes views for both regular users and admin users, handling tasks such as document
management and batch processing.
"""

import json
import logging
import os

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render

from .models import DocumentBatch, PlumbingDocument, ProcessedDocument, ProcessedImage
from .utils.process_final_data import process_all_data

logger = logging.getLogger(__name__)


def is_staff_user(user):
    """Check if the user is a staff member.

    Args:
        user: The user to check.

    Returns:
        bool: True if the user is a staff member, False otherwise.
    """
    return user.is_staff


def home(request: HttpRequest) -> HttpResponse:
    """Render the home page.

    Args:
        request: The HTTP request object.

    Returns:
        The rendered home page.
    """
    if request.user.is_authenticated and request.user.is_staff:
        return render(request, "main/admin/home.html")
    return render(request, "main/home.html")


def login_view(request: HttpRequest) -> HttpResponse:
    """Handle user login.

    Args:
        request: The HTTP request object.

    Returns:
        The rendered login page or redirects to the home page after successful login.
    """
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


def register(request: HttpRequest) -> HttpResponse:
    """Handle user registration.

    Args:
        request: The HTTP request object.

    Returns:
        The rendered registration page or redirects to the home page after successful registration.
    """
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
def profile(request: HttpRequest) -> HttpResponse:
    """Render the user's profile page.

    Args:
        request: The HTTP request object.

    Returns:
        The rendered profile page.
    """
    # Get user's document batches
    batches = DocumentBatch.objects.filter(user=request.user).order_by("-created_at")
    search_count = batches.count()
    doc_count = sum(batch.documents.count() for batch in batches)

    # Common context for both admin and regular users
    context = {
        "search_count": search_count,
        "doc_count": doc_count,
        "recent_activities": [],  # Replace with actual activities from database
    }

    # Add admin-specific stats for admin users
    if request.user.is_staff:
        # Get system-wide statistics
        total_batches = DocumentBatch.objects.count()
        total_users = User.objects.count()
        total_docs = ProcessedDocument.objects.count()
        successful_docs = ProcessedDocument.objects.filter(status="success").count()

        context.update(
            {
                "total_batches": total_batches,
                "total_users": total_users,
                "total_docs": total_docs,
                "successful_docs": successful_docs,
                "success_rate": ((successful_docs / total_docs * 100) if total_docs > 0 else 0),
            }
        )
        template_name = "main/admin/profile.html"
    else:
        template_name = "main/user/profile.html"

    return render(request, template_name, context)


@login_required
def semantic_search(request):
    """View for semantic search using document embeddings.

    Args:
        request: The HTTP request object.

    Returns:
        The rendered search page.
    """
    context = {"results": [], "error": None}

    if request.method == "POST":
        query = request.POST.get("query")
        if query:
            try:
                # Find the latest embeddings file
                embeddings_dir = os.path.join(settings.MEDIA_ROOT, "plumbing_code", "embeddings")
                logger.info(f"Looking for embeddings in directory: {embeddings_dir}")

                if not os.path.exists(embeddings_dir):
                    raise FileNotFoundError(f"No embeddings directory found at {embeddings_dir}")

                # Load embeddings and perform search
                context["results"] = []  # For now, return empty results
                context["query"] = query

            except Exception as e:
                context["error"] = f"Error performing search: {str(e)}"

    return render(request, "main/semantic_search.html", context)


@user_passes_test(is_staff_user)
def process_upload(request: HttpRequest) -> JsonResponse:
    """Handle file upload.

    Args:
        request: The HTTP request object.

    Returns:
        JSON response indicating success or failure of upload.
    """
    if request.method == "POST":
        try:
            logger.info("Starting file upload process")
            if not request.FILES:
                logger.warning("No files found in request.FILES")
                return JsonResponse(
                    {"status": "error", "message": "No files were uploaded."}, status=400
                )

            files = request.FILES.getlist("images")
            logger.info(f"Found {len(files)} files in request")
            if not files:
                logger.warning("No files found in images field")
                return JsonResponse(
                    {"status": "error", "message": "No files were selected."}, status=400
                )

            upload_dir = os.path.join(settings.MEDIA_ROOT, "plumbing_code", "uploads")
            logger.info(f"Using upload directory: {upload_dir}")
            os.makedirs(upload_dir, exist_ok=True)

            uploaded_files = []
            for file in files:
                logger.info(f"Processing file: {file.name}")
                if not file.name.lower().endswith((".png", ".jpg", ".jpeg")):
                    error_msg = (
                        f"Invalid file type for {file.name}. Only PNG and JPG files are allowed."
                    )
                    logger.warning(error_msg)
                    return JsonResponse({"status": "error", "message": error_msg}, status=400)

                # Save the file to the uploads directory
                file_path = os.path.join(upload_dir, file.name)
                logger.info(f"Saving file to: {file_path}")
                with open(file_path, "wb+") as destination:
                    for chunk in file.chunks():
                        destination.write(chunk)
                uploaded_files.append(file.name)
                logger.info(f"Successfully saved file: {file.name}")

            logger.info(f"Upload complete. {len(uploaded_files)} files uploaded successfully")
            return JsonResponse(
                {
                    "status": "success",
                    "message": f"Successfully uploaded {len(uploaded_files)} files",
                    "files": uploaded_files,
                }
            )
        except Exception as e:
            error_msg = f"Upload failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return JsonResponse({"status": "error", "message": error_msg}, status=500)

    elif request.method == "GET":
        return render(request, "main/admin/process.html")

    return JsonResponse({"status": "error", "message": "Invalid request method"}, status=400)


@user_passes_test(is_staff_user)
def start_processing(request: HttpRequest) -> JsonResponse:
    """Start processing all uploaded images.

    Args:
        request: The HTTP request object.

    Returns:
        JSON response indicating success or failure of processing start.
    """
    if request.method == "POST":
        try:
            from .utils.process_start import main as process_start_main

            process_start_main()
            return JsonResponse(
                {"status": "success", "message": "Processing completed successfully"}
            )
        except Exception as e:
            logger.error(f"Error during processing: {str(e)}")
            return JsonResponse(
                {"status": "error", "message": f"Processing failed: {str(e)}"}, status=500
            )

    return JsonResponse({"status": "error", "message": "Invalid request method"}, status=400)


@login_required
@user_passes_test(is_staff_user)
def process_plumbing_data(request: HttpRequest) -> JsonResponse:
    """Process plumbing code data (JSON files, images, and tables).

    Args:
        request: The HTTP request object.

    Returns:
        JSON response indicating success or failure of processing.
    """
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Invalid request method"})

    try:
        # Process data using the current user
        process_all_data(request.user)
        return JsonResponse({"success": True})
    except Exception as e:
        logger.error(f"Error processing plumbing data: {str(e)}")
        return JsonResponse({"success": False, "error": str(e)})


@user_passes_test(is_staff_user)
def view_batch_chapters(request: HttpRequest) -> HttpResponse:
    """View processed chapters from the database.

    Args:
        request: The HTTP request object.

    Returns:
        The rendered batch chapters page.
    """
    try:
        # Get all documents for the current user
        documents = PlumbingDocument.objects.filter(user=request.user).prefetch_related(
            "images", "tables"
        )

        chapters_data = []
        for doc in documents:
            # Get all images and tables for this document
            images = doc.images.all().order_by("page_number")
            tables = doc.tables.all().order_by("page_number")

            # Create a dictionary of pages with their associated data
            pages = {}
            for img in images:
                pages[img.page_number] = {
                    "page_number": img.page_number,
                    "image_url": img.image.url if img.image else None,
                    "table_content": None,
                    "text_content": "",
                }

            for table in tables:
                if table.page_number in pages:
                    pages[table.page_number]["table_content"] = table.csv_content
                else:
                    pages[table.page_number] = {
                        "page_number": table.page_number,
                        "image_url": None,
                        "table_content": table.csv_content,
                        "text_content": "",
                    }

            # Add text content from JSON if available
            if doc.json_content and "f" in doc.json_content:
                for item in doc.json_content["f"]:
                    page_num = item.get("i")
                    if page_num and page_num in pages:
                        pages[page_num]["text_content"] = item.get("t", "")

            # Sort pages by page number
            sorted_pages = [pages[num] for num in sorted(pages.keys())]

            chapter_data = {
                "filename": doc.title,
                "pages": sorted_pages,
                "json_url": f"/media/plumbing_code/json_final/{doc.title}.json",
            }
            chapters_data.append(chapter_data)

        return render(request, "main/admin/chapters.html", {"chapters": chapters_data})

    except Exception as e:
        logger.error(f"Error viewing chapters: {str(e)}")
        messages.error(request, f"Error viewing chapters: {str(e)}")
        return render(request, "main/admin/chapters.html", {"chapters": []})


@user_passes_test(is_staff_user)
def cleanup_intermediate_dirs(request: HttpRequest) -> JsonResponse:
    """Clean up intermediate processing directories.

    Args:
        request: The HTTP request object.

    Returns:
        JSON response indicating success or failure of cleanup.
    """
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Invalid request method"}, status=400)

    try:
        from django.core.management import call_command

        call_command("clean_intermediate_dirs")
        return JsonResponse(
            {"status": "success", "message": "Successfully cleaned up intermediate directories"}
        )
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")
        return JsonResponse(
            {"status": "error", "message": f"Error during cleanup: {str(e)}"}, status=500
        )


def logout_view(request: HttpRequest) -> HttpResponse:
    """Handle user logout.

    Args:
        request: The HTTP request object.

    Returns:
        Redirects to the home page after successful logout.
    """
    if request.method in ["GET", "POST"]:
        logout(request)
        messages.success(request, "You have been logged out successfully.")
        return redirect("home")  # Using named URL pattern
