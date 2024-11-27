"""Views for the main application.

This module contains all the view functions for handling web requests in the main application.
It includes views for both regular users and admin users, handling tasks such as image processing
and document management.
"""

import glob
import json
import logging
import os
import shutil
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.db import transaction
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods
from PIL import Image as PILImage

from .models import DocumentBatch, ProcessedDocument, ProcessedImage
from .utils.doc_classic import DocClassicProcessor
from .utils.embed_open import DocumentEmbedder
from .utils.image_groq import GroqImageProcessor
from .utils.image_llama import LlamaImageProcessor
from .utils.image_open import OpenAIImageProcessor
from .utils.image_processor import ImageProcessor

logger = logging.getLogger(__name__)


def home(request: HttpRequest) -> HttpResponse:
    """Render the home page.

    Args:
        request: The HTTP request object.

    Returns:
        The rendered home page.
    """
    return render(request, "main/user/home.html")


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


@staff_member_required
def image_llama(request: HttpRequest) -> HttpResponse:
    """Handle image processing using LlamaImageProcessor.

    Args:
        request: The HTTP request object.

    Returns:
        The rendered image processing page or redirects to home after successful processing.
    """
    if request.method == "POST" and request.FILES.get("image"):
        try:
            # Get the uploaded file
            uploaded_file = request.FILES["image"]

            # Check if it's a PNG file
            if not uploaded_file.name.lower().endswith(".png"):
                messages.error(
                    request,
                    "Please upload a PNG file.",
                )
                return render(
                    request,
                    "main/admin/image_llama.html",
                )

            # Save the file temporarily
            png_directory = os.path.join(settings.BASE_DIR, "main", "static", "images", "png_files")
            if not os.path.exists(png_directory):
                os.makedirs(png_directory)

            file_path = os.path.join(png_directory, uploaded_file.name)
            with open(file_path, "wb+") as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)

            # Initialize the processor and process the image
            processor = LlamaImageProcessor()
            result = processor.convert_png_to_pdf(file_path)

            # Clean up the temporary file
            os.remove(file_path)

            # Structure the results
            results = [
                {
                    "filename": uploaded_file.name,
                    "data": {
                        "table_summary": result.get("content", ""),
                        "success": result.get("success", False),
                        "message": result.get("message", ""),
                        "status": result.get("status", "failed"),
                        "pdf_path": result.get("pdf_path", ""),
                    },
                }
            ]

            return render(
                request,
                "main/admin/image_llama.html",
                {"results": results, "success": True},
            )

        except Exception as e:
            messages.error(request, f"Error processing image: {str(e)}")
            return render(request, "main/admin/image_llama.html")

    # If no file uploaded, just show the form
    return render(request, "main/admin/image_llama.html")


@staff_member_required
def image_open(request: HttpRequest) -> HttpResponse:
    """Handle image processing using OpenAIImageProcessor.

    Args:
        request: The HTTP request object.

    Returns:
        The rendered image processing page or redirects to home after successful processing.
    """
    try:
        if request.method == "POST" and request.FILES.get("image"):
            # Get the uploaded file
            uploaded_file = request.FILES["image"]

            # Check if it's a PNG file
            if not uploaded_file.name.lower().endswith(".png"):
                return render(
                    request,
                    "main/admin/image_open.html",
                    {
                        "response": {
                            "success": False,
                            "message": "Please upload a PNG file.",
                            "status": "failed",
                        }
                    },
                )

            # Save the file temporarily
            png_directory = os.path.join(settings.BASE_DIR, "main", "static", "images", "png_files")
            if not os.path.exists(png_directory):
                os.makedirs(png_directory)

            image_path = os.path.join(png_directory, str(time.time()) + "_" + uploaded_file.name)
            with open(image_path, "wb+") as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)

            # Initialize the processor
            processor = OpenAIImageProcessor()

            # Process the image
            result = processor.analyze_image(image_path)

            # Format the response
            response = {
                "success": True,
                "message": "Image processed successfully",
                "status": "completed",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "results": [
                    {
                        "filename": uploaded_file.name,
                        "success": result["success"],
                        "data": {
                            "table_summary": "",
                            "table_headers": [],
                            "table_data": [],
                        },
                        "analysis": result["analysis"],  # Add the analysis directly to the result
                    }
                ],
            }

            # Add debug print
            print("Response data:", response)

            return render(request, "main/admin/image_open.html", {"results": response["results"]})

        # If no file uploaded, just show the form
        return render(request, "main/admin/image_open.html")

    except Exception as e:
        return render(
            request,
            "main/admin/image_open.html",
            {
                "response": {
                    "success": False,
                    "message": f"Error processing image: {str(e)}",
                    "status": "failed",
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
            },
        )


@staff_member_required
def image_groq(request: HttpRequest) -> HttpResponse:
    """Handle image processing using GroqImageProcessor.

    Args:
        request: The HTTP request object.

    Returns:
        The rendered image processing page or redirects to home after successful processing.
    """
    import logging
    import os
    import time

    logger = logging.getLogger(__name__)

    results = []
    pdf_url = None

    try:
        if request.method == "POST" and request.FILES.get("image"):
            # Initialize processor
            from .utils.image_groq import GroqImageProcessor

            processor = GroqImageProcessor()
            logger.info("GroqImageProcessor initialized successfully")

            # Get the uploaded file
            uploaded_file = request.FILES["image"]

            # Get the file extension from the original filename
            file_extension = os.path.splitext(uploaded_file.name)[1].lower()

            # Validate file extension
            if file_extension not in [".pdf", ".jpg", ".jpeg", ".png"]:
                error_msg = (
                    "Invalid file type. Please upload PDF or image files " "(jpg, jpeg, png)."
                )
                messages.error(request, error_msg)
                return redirect("process_doc_classic")

            # Save the file temporarily
            png_directory = os.path.join(settings.BASE_DIR, "main", "static", "images", "png_files")
            if not os.path.exists(png_directory):
                os.makedirs(png_directory)

            image_path = os.path.join(png_directory, str(time.time()) + "_" + uploaded_file.name)
            with open(image_path, "wb+") as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)

            # Process the image
            start_time = time.time()
            result = processor.process_image(image_path)
            processing_time = round(time.time() - start_time, 2)

            # Clean up the temporary file
            if os.path.exists(image_path):
                os.remove(image_path)

            # Structure the results
            results = [
                {
                    "filename": uploaded_file.name,
                    "processing_time": processing_time,
                    "data": {
                        "success": result.get("success", False),
                        "status": "completed",
                        "table_headers": result.get("table_headers", []),
                        "table_data": result.get("table_data", []),
                        "table_summary": result.get("table_summary", ""),
                        "content": result.get("content", ""),
                    },
                }
            ]

            logger.info(f"Successfully processed {uploaded_file.name}")

            return render(request, "main/admin/image_groq.html", {"results": results})

    except Exception as e:
        logger.error(f"Error processing image: {str(e)}", exc_info=True)
        messages.error(request, f"Error processing image: {str(e)}")

    return render(request, "main/admin/image_groq.html", {"results": results})


def _encode_image(image_path: str) -> str:
    """Encode an image to base64."""
    with PILImage.open(image_path) as img:
        # Convert to RGB if necessary
        if img.mode != "RGB":
            img = img.convert("RGB")


@staff_member_required
def process_doc_classic(request: HttpRequest) -> HttpResponse:
    """Handle document processing using DocClassicProcessor.

    Args:
        request: The HTTP request object.

    Returns:
        The rendered document processing page or redirects after successful
        processing.
    """
    processor = DocClassicProcessor()
    context = {"results": [], "stats": None, "search_results": None, "search_query": None}

    try:
        # Get document statistics
        context["stats"] = processor.get_document_stats()

        # Handle search
        search_query = request.GET.get("search")
        if search_query:
            context["search_results"] = processor.search_documents(search_query)
            context["search_query"] = search_query

        if request.method == "POST":
            if request.FILES.getlist("documents"):
                # Handle multiple file upload
                documents = request.FILES.getlist("documents")
                temp_dir = os.path.join(settings.MEDIA_ROOT, "temp", str(uuid.uuid4()))
                os.makedirs(temp_dir, exist_ok=True)

                # Save uploaded files to temp directory
                for document in documents:
                    doc_path = os.path.join(temp_dir, str(time.time()) + "_" + document.name)
                    with open(doc_path, "wb+") as destination:
                        for chunk in document.chunks():
                            destination.write(chunk)

                # Process the folder
                batch_result = processor.process_folder(
                    temp_dir,
                    batch_name=f"Upload {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    user=request.user,
                )

                # Get batch info and prepare results
                batch = DocumentBatch.objects.get(id=batch_result["batch_id"])
                successful_docs = batch.documents.filter(status="success")

                for doc in successful_docs:
                    context["results"].append(
                        {
                            "id": doc.id,
                            "filename": doc.filename,
                            "title": doc.title,
                            "chapter": doc.chapter,
                            "section_pc": doc.section_pc,
                            "section": doc.section,
                            "subsection": doc.subsection,
                            "original_url": doc.original_url,
                            "text_url": doc.text_url,
                            "text": doc.get_text_content(),
                            "ocr_confidence": doc.ocr_confidence,
                            "ocr_version": doc.ocr_version,
                            "created_at": doc.created_at,
                            "status": doc.status,
                            "is_duplicate": doc.is_duplicate,
                            "processing_params": doc.processing_params,
                        }
                    )

                messages.success(
                    request,
                    f"Successfully processed {batch_result['successful']} out of "
                    f"{batch_result['total_documents']} documents. "
                    f"Batch ID: {batch_result['batch_id']}",
                    extra_tags="long-message",
                )

                # Clean up temp directory
                shutil.rmtree(temp_dir)

            elif request.FILES.get("document"):
                # Handle single file upload
                document = request.FILES["document"]
                temp_dir = os.path.join(settings.MEDIA_ROOT, "temp", str(uuid.uuid4()))
                os.makedirs(temp_dir, exist_ok=True)
                doc_path = os.path.join(temp_dir, str(time.time()) + "_" + document.name)

                # Save file temporarily
                with open(doc_path, "wb+") as destination:
                    for chunk in document.chunks():
                        destination.write(chunk)

                # Process as a single-file batch
                batch_result = processor.process_folder(
                    temp_dir, batch_name=f"Single {document.name}", user=request.user
                )

                if batch_result["successful"] > 0:
                    # Get the processed document
                    doc = ProcessedDocument.objects.filter(
                        batch_id=batch_result["batch_id"], status="success"
                    ).first()

                    if doc:
                        context["results"].append(
                            {
                                "id": doc.id,
                                "filename": doc.filename,
                                "title": doc.title,
                                "chapter": doc.chapter,
                                "section_pc": doc.section_pc,
                                "section": doc.section,
                                "subsection": doc.subsection,
                                "original_url": doc.original_url,
                                "text_url": doc.text_url,
                                "text": doc.get_text_content(),
                                "ocr_confidence": doc.ocr_confidence,
                                "ocr_version": doc.ocr_version,
                                "created_at": doc.created_at,
                                "status": doc.status,
                                "is_duplicate": doc.is_duplicate,
                                "processing_params": doc.processing_params,
                            }
                        )
                        messages.success(request, "Document processed successfully!")
                    else:
                        messages.error(request, "Document processing failed.")

                # Clean up temp directory
                shutil.rmtree(temp_dir)

    except ValueError as e:
        messages.error(request, str(e))
    except Exception as e:
        messages.error(request, f"Error processing document(s): {str(e)}")
    finally:
        processor.cleanup()

    return render(request, "main/admin/doc_classic.html", context)


@staff_member_required
def view_document_batches(request: HttpRequest) -> HttpResponse:
    """View all document batches. Admin only.

    Args:
        request: The HTTP request object.

    Returns:
        The rendered document batches page.
    """
    batches = DocumentBatch.objects.all().order_by("-created_at")
    return render(request, "main/admin/doc_batches.html", {"batches": batches})


@staff_member_required
def view_batch_details(request: HttpRequest, batch_id: str) -> HttpResponse:
    """View details of a specific document batch. Admin only.

    Args:
        request: The HTTP request object.
        batch_id: The ID of the document batch.

    Returns:
        The rendered batch details page.
    """
    try:
        batch = DocumentBatch.objects.get(id=batch_id)
        documents = batch.documents.all().order_by("-processed_at")

        # Calculate success rate
        total_docs = documents.count()
        successful_docs = documents.filter(status="success").count()
        batch.successful_documents = (successful_docs / total_docs * 100) if total_docs > 0 else 0

        return render(
            request,
            "main/admin/doc_batch_details.html",
            {"batch": batch, "documents": documents},
        )
    except DocumentBatch.DoesNotExist:
        messages.error(request, "Batch not found.")
        return redirect("doc_batches")


@staff_member_required
def delete_batch(request: HttpRequest, batch_id: str) -> HttpResponse:
    """Delete a document batch and all its associated files. Admin only.

    Args:
        request: The HTTP request object.
        batch_id: The ID of the document batch.

    Returns:
        Redirects to the document batches page after successful deletion.
    """
    if request.method == "POST":
        try:
            with transaction.atomic():
                # Get the batch with a select_for_update to lock the row
                batch = DocumentBatch.objects.select_for_update().get(id=batch_id)

                # Get all documents in the batch
                documents = ProcessedDocument.objects.select_for_update().filter(batch=batch)

                # Delete each document's files if they exist
                for doc in documents:
                    # Delete original file if it exists
                    if hasattr(doc, "original_file"):
                        try:
                            # Check if the file field has an actual file
                            if doc.original_file and doc.original_file.name:
                                storage = doc.original_file.storage
                                if storage.exists(doc.original_file.name):
                                    storage.delete(doc.original_file.name)
                        except Exception as e:
                            logger.warning(
                                f"Error deleting original file for document {doc.id}: {str(e)}"
                            )

                    # Delete text content if it exists
                    if hasattr(doc, "text_content"):
                        try:
                            # Check if the file field has an actual file
                            if doc.text_content and doc.text_content.name:
                                storage = doc.text_content.storage
                                if storage.exists(doc.text_content.name):
                                    storage.delete(doc.text_content.name)
                        except Exception as e:
                            logger.warning(
                                f"Error deleting text content for document {doc.id}: {str(e)}"
                            )

                # Delete the batch first (this will cascade delete documents)
                batch.delete()

                messages.success(request, "Batch and associated files deleted successfully.")

        except DocumentBatch.DoesNotExist:
            messages.error(request, "Batch not found.")
        except Exception as e:
            logger.error(f"Error in delete_batch: {str(e)}")
            messages.error(request, "Error deleting batch. Please try again or contact support.")

    return redirect("doc_batches")


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


@login_required
def semantic_search(request: HttpRequest) -> HttpResponse:
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
                # Initialize embedder
                embedder = DocumentEmbedder()

                # Find the latest embeddings file
                embeddings_dir = os.path.join(settings.MEDIA_ROOT, "embeddings")
                embedding_files = glob.glob(os.path.join(embeddings_dir, "embeddings_*.json"))
                if not embedding_files:
                    raise FileNotFoundError("No embedding files found")

                latest_embedding_file = max(embedding_files, key=os.path.getctime)

                # Load embeddings and perform search
                embeddings_data = embedder.load_embeddings(latest_embedding_file)
                results = embedder.search_documents(query, embeddings_data, top_k=5)

                context["results"] = results
                context["query"] = query

            except Exception as e:
                context["error"] = f"Error performing search: {str(e)}"

    return render(request, "main/user/embed_open.html", context)


@staff_member_required
def upload_file(request: HttpRequest) -> HttpResponse:
    """Handle file upload.

    Args:
        request: The HTTP request object.

    Returns:
        The rendered file upload page or redirects to the home page after successful upload.
    """
    if request.method == "POST":
        # Get the uploaded file
        uploaded_file = request.FILES.get("file")
        if not uploaded_file:
            messages.error(request, "No file was uploaded.")
            return redirect("upload")

        # Check file type
        file_ext = os.path.splitext(uploaded_file.name)[1].lower()
        if file_ext not in [".jpg", ".jpeg", ".png", ".pdf"]:
            messages.error(request, "Invalid file type. Please upload a JPG, PNG, or PDF file.")
            return redirect("upload")

        # Create a unique filename
        filename = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(settings.MEDIA_ROOT, "uploads", str(request.user.id), filename)

        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # Save the file
        with open(file_path, "wb+") as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)

        messages.success(request, "File uploaded successfully!")
        return redirect("home")

    return render(request, "main/admin/upload_file.html")


def process_document(request: HttpRequest, document_id: int) -> JsonResponse:
    """Process a document and return embedding results."""
    try:
        doc = get_object_or_404(ProcessedDocument, id=document_id)
        proc = DocClassicProcessor()
        result = proc.process_document(doc.original_path)
        return JsonResponse({"status": "success", "result": result})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


def process_image(request: HttpRequest, image_id: int) -> JsonResponse:
    """Process an image and return analysis results."""
    try:
        from .models import ProcessedImage
        from .utils.image_processor import ImageProcessor

        image = ProcessedImage.objects.get(id=image_id)
        processor = ImageProcessor()
        result = processor.process_image(image.image.path)
        return JsonResponse({"success": True, "result": result})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


def process_image_batch(request: HttpRequest) -> JsonResponse:
    """Process multiple images and return analysis results."""
    try:
        img_ids = json.loads(request.body)["image_ids"]
        image_paths = []
        for img_id in img_ids:
            image_path = os.path.join(settings.MEDIA_ROOT, "images", f"{img_id}.png")
            if os.path.exists(image_path):
                image_paths.append(image_path)
        proc = GroqImageProcessor()
        results = proc.process_image_batch(image_paths)
        return JsonResponse({"status": "success", "results": results})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


def process_image_with_text(request: HttpRequest, image_id: int) -> JsonResponse:
    """Process an image with text prompt and return analysis results."""
    try:
        image_path = os.path.join(settings.MEDIA_ROOT, "images", f"{image_id}.png")
        if not os.path.exists(image_path):
            return JsonResponse({"status": "error", "message": "Image not found"}, status=404)
        text = json.loads(request.body)["text"]
        proc = GroqImageProcessor()
        result = proc.process_image_with_text(image_path, text)
        return JsonResponse({"status": "success", "result": result})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)
