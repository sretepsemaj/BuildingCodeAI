from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.shortcuts import redirect, render
from django.conf import settings
import os
from datetime import datetime
from .utils.image_llama import LlamaImageProcessor
from .utils.doc_classic import DocClassicProcessor
import uuid
import shutil
from .models import ProcessedDocument, DocumentBatch

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
    # You can add database queries here to get actual counts and activities
    context = {
        'gpt4_count': 0,  # Replace with actual count from database
        'llama_count': 0,  # Replace with actual count from database
        'groq_count': 0,   # Replace with actual count from database
        'recent_activities': []  # Replace with actual activities from database
    }
    return render(request, "main/profile.html", context)


@login_required
def image_llama(request):
    if request.method == 'POST' and request.FILES.get('image'):
        try:
            # Get the uploaded file
            uploaded_file = request.FILES['image']
            
            # Check if it's a PNG file
            if not uploaded_file.name.lower().endswith('.png'):
                messages.error(request, 'Please upload a PNG file.')
                return render(request, 'main/image_llama.html')
            
            # Save the file temporarily
            png_directory = os.path.join(settings.BASE_DIR, 'main', 'static', 'images', 'png_files')
            if not os.path.exists(png_directory):
                os.makedirs(png_directory)
            
            file_path = os.path.join(png_directory, uploaded_file.name)
            with open(file_path, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)
            
            # Initialize the processor and process the image
            processor = LlamaImageProcessor()
            result = processor.convert_png_to_pdf(file_path)
            
            # Clean up the temporary file
            os.remove(file_path)
            
            # Structure the results for the template
            results = [{
                'filename': uploaded_file.name,
                'data': {
                    'table_summary': result.get('content', ''),
                    'success': result.get('success', False),
                    'message': result.get('message', ''),
                    'status': result.get('status', 'failed'),
                    'pdf_path': result.get('pdf_path', '')
                }
            }]
            
            return render(request, 'main/image_llama.html', {
                'results': results,
                'success': True
            })
            
        except Exception as e:
            messages.error(request, f'Error processing image: {str(e)}')
            return render(request, 'main/image_llama.html')
    
    # If no file uploaded, just show the form
    return render(request, 'main/image_llama.html')


@login_required
def image_open(request):
    from .utils.image_open import OpenAIImageProcessor
    
    try:
        if request.method == 'POST' and request.FILES.get('image'):
            # Get the uploaded file
            uploaded_file = request.FILES['image']
            
            # Check if it's a PNG file
            if not uploaded_file.name.lower().endswith('.png'):
                return render(request, 'main/image_open.html', {
                    'response': {
                        'success': False,
                        'message': 'Please upload a PNG file.',
                        'status': 'failed'
                    }
                })
            
            # Save the file temporarily
            png_directory = os.path.join(settings.BASE_DIR, 'main', 'static', 'images', 'png_files')
            if not os.path.exists(png_directory):
                os.makedirs(png_directory)
            
            file_path = os.path.join(png_directory, uploaded_file.name)
            with open(file_path, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)
            
            # Initialize the processor
            processor = OpenAIImageProcessor()
            
            # Process the image
            result = processor.analyze_image(file_path)
            
            # Format the response
            response = {
                'success': True,
                'message': 'Image processed successfully',
                'status': 'completed',
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'results': [{
                    'filename': uploaded_file.name,
                    'success': True,
                    'data': {
                        'table_summary': result['analysis'],
                        'table_headers': [],
                        'table_data': []
                    }
                }]
            }
            
            # Add debug print
            print("Response data:", response)
            
            return render(request, 'main/image_open.html', {
                'results': response['results'],  # Pass results directly
                'png_directory': png_directory.replace(str(settings.BASE_DIR), '').lstrip('/')
            })
            
        # If no file uploaded, just show the form
        return render(request, 'main/image_open.html')
        
    except Exception as e:
        return render(request, 'main/image_open.html', {
            'response': {
                'success': False,
                'message': f'Error processing image: {str(e)}',
                'status': 'failed',
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        })


@login_required
def image_groq(request):
    """View for Groq image analysis."""
    import logging
    import time
    logger = logging.getLogger(__name__)
    
    results = []
    pdf_url = None

    try:
        if request.method == 'POST' and request.FILES.get('image'):
            # Initialize processor
            from .utils.image_groq import GroqImageProcessor
            processor = GroqImageProcessor()
            logger.info("GroqImageProcessor initialized successfully")
            
            # Get the uploaded file
            uploaded_file = request.FILES['image']
            
            # Process the image
            start_time = time.time()
            image_data = uploaded_file.read()
            result = processor.process_image(image_data)
            processing_time = round(time.time() - start_time, 2)
            
            # Structure the results
            results = [{
                'filename': uploaded_file.name,
                'processing_time': processing_time,
                'data': {
                    'success': True,
                    'status': 'completed',
                    'table_headers': result.get('table_headers', []),
                    'table_data': result.get('table_data', []),
                    'table_summary': result.get('table_summary', ''),
                    'content': result.get('content', '')
                }
            }]
            
            logger.info(f"Successfully processed {uploaded_file.name}")
            
    except Exception as e:
        logger.error(f"Error processing image: {str(e)}", exc_info=True)
        messages.error(request, f"Error processing image: {str(e)}")
    
    return render(request, 'main/image_groq.html', {
        'results': results
    })


@login_required
def process_doc_classic(request):
    results = []
    if request.method == 'POST':
        processor = DocClassicProcessor()
        
        try:
            if request.FILES.getlist('documents'):
                # Handle multiple file upload
                documents = request.FILES.getlist('documents')
                temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp', str(uuid.uuid4()))
                os.makedirs(temp_dir, exist_ok=True)
                
                # Save uploaded files to temp directory
                for document in documents:
                    file_path = os.path.join(temp_dir, document.name)
                    with open(file_path, 'wb+') as destination:
                        for chunk in document.chunks():
                            destination.write(chunk)
                
                # Process the folder
                batch_result = processor.process_folder(
                    temp_dir,
                    batch_name=f"Upload {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    user=request.user
                )
                
                # Get batch info and prepare results
                batch = DocumentBatch.objects.get(id=batch_result['batch_id'])
                successful_docs = batch.documents.filter(status='success')
                
                for doc in successful_docs:
                    results.append({
                        'filename': doc.filename,
                        'original_url': doc.original_url,
                        'text_url': doc.text_url,
                        'text': doc.get_text_content()
                    })
                
                messages.success(
                    request,
                    f"Successfully processed {batch_result['successful']} out of {batch_result['total_documents']} documents. Batch ID: {batch_result['batch_id']}"
                )
                
                # Clean up temp directory
                shutil.rmtree(temp_dir)
            
            elif request.FILES.get('document'):
                # Handle single file upload
                document = request.FILES['document']
                temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp', str(uuid.uuid4()))
                os.makedirs(temp_dir, exist_ok=True)
                file_path = os.path.join(temp_dir, document.name)
                
                # Save file temporarily
                with open(file_path, 'wb+') as destination:
                    for chunk in document.chunks():
                        destination.write(chunk)
                
                # Process as a single-file batch
                batch_result = processor.process_folder(
                    temp_dir,
                    batch_name=f"Single {document.name}",
                    user=request.user
                )
                
                if batch_result['successful'] > 0:
                    # Get the processed document
                    doc = ProcessedDocument.objects.filter(
                        batch_id=batch_result['batch_id'],
                        status='success'
                    ).first()
                    
                    if doc:
                        results.append({
                            'filename': doc.filename,
                            'original_url': doc.original_url,
                            'text_url': doc.text_url,
                            'text': doc.get_text_content()
                        })
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
    
    return render(request, 'main/doc_classic.html', {'results': results})


@login_required
def view_document_batches(request):
    """View all document batches for the current user."""
    batches = DocumentBatch.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'main/doc_batches.html', {'batches': batches})


@login_required
def view_batch_details(request, batch_id):
    """View details of a specific document batch."""
    try:
        batch = DocumentBatch.objects.get(id=batch_id, user=request.user)
        documents = batch.documents.all().order_by('-processed_at')
        return render(request, 'main/doc_batch_details.html', {
            'batch': batch,
            'documents': documents
        })
    except DocumentBatch.DoesNotExist:
        messages.error(request, "Batch not found.")
        return redirect('view_document_batches')


@login_required
def delete_batch(request, batch_id):
    """Delete a document batch and all its associated files."""
    if request.method == "POST":
        try:
            batch = DocumentBatch.objects.get(id=batch_id, user=request.user)
            
            # Delete associated documents first
            documents = ProcessedDocument.objects.filter(batch=batch)
            for doc in documents:
                try:
                    # Delete the physical files
                    if doc.original_path:
                        full_path = os.path.join(settings.MEDIA_ROOT, doc.original_path.lstrip('/'))
                        if os.path.exists(full_path):
                            os.remove(full_path)
                            
                    if doc.text_path:
                        full_path = os.path.join(settings.MEDIA_ROOT, doc.text_path.lstrip('/'))
                        if os.path.exists(full_path):
                            os.remove(full_path)
                except Exception as e:
                    print(f"Error deleting files for document {doc.id}: {e}")
                
                # Delete the document record
                try:
                    doc.delete()
                except Exception as e:
                    print(f"Error deleting document record {doc.id}: {e}")

            # Delete the batch itself
            batch.delete()
            messages.success(request, 'Batch deleted successfully.')
            
        except DocumentBatch.DoesNotExist:
            messages.error(request, 'Batch not found.')
        except Exception as e:
            print(f"Error in delete_batch: {e}")
            messages.error(request, f'Error deleting batch: {str(e)}')
    
    return redirect('view_document_batches')


def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect("home")
