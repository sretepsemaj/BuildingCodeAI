from dotenv import load_dotenv
import os
from llama_parse import LlamaParse
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex
from llama_index.llms.openai import OpenAI
import base64
import tempfile
from PIL import Image
import io
from typing import List, Dict
from openai import OpenAI as OpenAIClient

class LlamaImageProcessor:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        self.api_key = os.getenv('LAMA_API_KEY')
        if not self.api_key:
            raise ValueError("LAMA_API_KEY not found in environment variables")
        print(f"Using API key: {self.api_key[:10]}...")
        
        # Initialize LlamaParse
        self.parser = LlamaParse(
            api_key=self.api_key,
            result_type="markdown"
        )
        
        # Initialize OpenAI for querying
        self.openai_api_key = os.getenv('MYSK_API_KEY')
        if self.openai_api_key:
            self.llm = OpenAI(api_key=self.openai_api_key)
            self.vision_client = OpenAIClient(api_key=self.openai_api_key)
        else:
            self.llm = None
            self.vision_client = None
            print("Warning: MYSK_API_KEY not found, advanced image analysis will not be available")

    def encode_image(self, image_path: str) -> str:
        """Encode image to base64 for API submission"""
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            raise Exception(f"Error encoding image: {str(e)}")

    def analyze_with_gpt4_vision(self, image_path: str) -> dict:
        """Analyze image using GPT-4 Vision API"""
        try:
            if not self.vision_client:
                return {
                    'success': False,
                    'message': 'GPT-4 Vision not configured (missing API key)',
                    'analysis': ''
                }

            if not os.path.exists(image_path):
                return {
                    'success': False,
                    'message': f'Image file not found: {image_path}',
                    'analysis': ''
                }

            # Encode the image
            base64_image = self.encode_image(image_path)
            
            # Create the GPT-4 Vision request
            response = self.vision_client.chat.completions.create(
                model="gpt-4-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Please analyze this image in detail. If it's a graph or chart, describe its type, axes, trends, and key data points. If it contains text, extract and organize it. Include any relevant numerical values and relationships shown."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=1000
            )
            
            return {
                'success': True,
                'message': 'Image analyzed successfully with GPT-4 Vision',
                'analysis': response.choices[0].message.content
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error analyzing image with GPT-4 Vision: {str(e)}',
                'analysis': ''
            }

    def process_image(self, image_path: str) -> dict:
        """Process a single image using LlamaParse"""
        try:
            # Create a temporary directory to store our files
            with tempfile.TemporaryDirectory() as temp_dir:
                # Convert PNG to PDF if needed (LlamaParse works better with PDFs)
                if image_path.lower().endswith('.png'):
                    pdf_path = os.path.join(temp_dir, 'image.pdf')
                    img = Image.open(image_path)
                    img.save(pdf_path, 'PDF', resolution=100.0)
                else:
                    pdf_path = image_path
                
                # Use SimpleDirectoryReader to parse our file
                file_extractor = {".pdf": self.parser}
                documents = SimpleDirectoryReader(
                    input_files=[pdf_path],
                    file_extractor=file_extractor
                ).load_data()
                
                # Create an index if we have OpenAI available
                if self.llm and documents:
                    try:
                        index = VectorStoreIndex.from_documents(documents)
                        # Try a test query to verify the index works
                        query_engine = index.as_query_engine()
                        test_response = query_engine.query("What is this document about?")
                        return {
                            'success': True,
                            'message': 'Document processed successfully with OpenAI indexing',
                            'text_content': documents[0].text if documents else '',
                            'query_example': str(test_response)
                        }
                    except Exception as e:
                        # If OpenAI indexing fails, still return the text content
                        return {
                            'success': True,
                            'message': f'Document processed (OpenAI indexing failed: {str(e)})',
                            'text_content': documents[0].text if documents else ''
                        }
                else:
                    return {
                        'success': True,
                        'message': 'Document processed successfully (no OpenAI indexing)',
                        'text_content': documents[0].text if documents else ''
                    }
                
        except Exception as e:
            return {
                'success': False,
                'message': f'Error processing image: {str(e)}',
                'text_content': ''
            }
            
    def query_document(self, index, query: str) -> str:
        """Query a processed document using OpenAI"""
        if not self.llm:
            return "OpenAI API key not configured. Please set OPENAI_API_KEY in your environment."
        
        try:
            query_engine = index.as_query_engine()
            response = query_engine.query(query)
            return str(response)
        except Exception as e:
            print(f"Error querying document: {str(e)}")
            return f"Error: {str(e)}"

    def process_directory(self, directory_path: str) -> Dict:
        """Process all PNG files in a directory"""
        # Check if directory exists
        if not os.path.exists(directory_path):
            return {
                'success': False,
                'message': f'Directory not found: {directory_path}',
                'results': []
            }
            
        # Get list of files
        try:
            files = os.listdir(directory_path)
        except Exception as e:
            return {
                'success': False,
                'message': f'Error reading directory: {str(e)}',
                'results': []
            }
            
        if not files:
            return {
                'success': True,
                'message': 'No files found in directory',
                'results': []
            }
            
        results = []
        total_files = 0
        png_files = 0
        
        for filename in files:
            total_files += 1
            if filename.lower().endswith('.png'):
                png_files += 1
                file_path = os.path.join(directory_path, filename)
                result = self.process_image(file_path)
                results.append({
                    'filename': filename,
                    'result': result
                })
        
        if png_files == 0:
            return {
                'success': True,
                'message': f'No PNG files found in directory (found {total_files} other files)',
                'results': []
            }
            
        return {
            'success': True,
            'message': f'Processed {png_files} PNG files out of {total_files} total files',
            'results': results
        }

# Example usage:
if __name__ == "__main__":
    processor = LlamaImageProcessor()
    png_directory = "/Users/aaronjpeters/PlumbingCodeAi/BuildingCodeai/main/static/images/png_files"
    results = processor.process_directory(png_directory)