from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.shortcuts import redirect, render
from django.conf import settings
import os
from datetime import datetime
from .utils.image_llama import LlamaImageProcessor

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
    return render(request, "main/image_processor1.html")


@login_required
def image_llama(request):
    if request.method == 'POST' and request.FILES.get('image'):
        try:
            # Get the uploaded file
            uploaded_file = request.FILES['image']
            
            # Check if it's a PNG file
            if not uploaded_file.name.lower().endswith('.png'):
                return render(request, 'main/image_llama.html', {
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
            
            # Initialize the processor and process the image
            processor = LlamaImageProcessor()
            result = processor.convert_png_to_pdf(file_path)
            
            # Clean up the temporary file
            os.remove(file_path)
            
            # Add timestamp
            result['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Calculate section count (count occurrences of '#' at the start of lines)
            if result['success'] and result['content']:
                section_count = sum(1 for line in result['content'].split('\n') if line.strip().startswith('#'))
                result['section_count'] = section_count
            
            return render(request, 'main/image_llama.html', {
                'response': result
            })
            
        except Exception as e:
            return render(request, 'main/image_llama.html', {
                'response': {
                    'success': False,
                    'message': f'Error processing image: {str(e)}',
                    'status': 'failed'
                }
            })
    
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
            result = processor.process_image(file_path)
            
            # Format the response
            response = {
                'success': True,
                'message': 'Image processed successfully',
                'status': 'completed',
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'results': [{
                    'filename': uploaded_file.name,
                    'success': True,
                    'data': result
                }]
            }
            
            return render(request, 'main/image_open.html', {
                'response': response,
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
    logger = logging.getLogger(__name__)
    
    results = []
    pdf_url = None

    try:
        # Initialize processor
        from .utils.image_groq import GroqImageProcessor
        processor = GroqImageProcessor()
        logger.info("GroqImageProcessor initialized successfully")
        
        # Get path to png_files directory
        png_directory = os.path.join(settings.STATIC_ROOT, 'images', 'png_files')
        if not os.path.exists(png_directory):
            png_directory = os.path.join(settings.BASE_DIR, 'main', 'static', 'images', 'png_files')
        
        logger.info(f"Using PNG directory: {png_directory}")
        
        # List all files in directory
        files = os.listdir(png_directory)
        logger.info(f"Found files in directory: {files}")
        
        # Process each PNG file in the directory
        for filename in files:
            if filename.lower().endswith('.png'):
                file_path = os.path.join(png_directory, filename)
                logger.info(f"Processing file: {file_path}")
                try:
                    result = processor.process_image(file_path)
                    logger.info(f"Successfully processed {filename}. Result: {result}")
                    results.append({
                        'filename': filename,
                        'data': result
                    })
                except Exception as e:
                    logger.error(f"Error processing {filename}: {str(e)}")
                    results.append({
                        'filename': filename,
                        'data': {
                            'table_headers': [],
                            'table_data': [],
                            'table_summary': f'Error processing image: {str(e)}'
                        }
                    })
        
        logger.info(f"Total results processed: {len(results)}")
        
        # Generate PDF report if we have results
        if results:
            output_filename = f'table_analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
            output_path = os.path.join(settings.MEDIA_ROOT, 'reports', output_filename)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            processor.generate_pdf_report(results, output_path)
            pdf_url = f'{settings.MEDIA_URL}reports/{output_filename}'
            logger.info(f"Generated PDF report: {output_path}")
        
    except Exception as e:
        logger.error(f"Error in image_groq view: {str(e)}", exc_info=True)
        messages.error(request, f'Error processing images: {str(e)}')
    
    context = {
        'results': results,
        'pdf_url': pdf_url
    }
    logger.info(f"Rendering template with context: {context}")
    
    return render(request, 'main/image_groq.html', context)


def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect("home")
