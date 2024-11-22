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
            result_type="markdown"  # "markdown" and "text" are available
        )
        
        # Initialize OpenAI for querying (if OPENAI_API_KEY is available)
        self.openai_api_key = os.getenv('MYSK_API_KEY')
        if self.openai_api_key:
            self.llm = OpenAI(api_key=self.openai_api_key)
        else:
            self.llm = None
            print("Warning: MYSK_API_KEY not found, querying will not be available")
    
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
    png_directory = "/Users/aaronjpeters/PlumbingCodeAi/BuildingCodeai/main/static/images"
    results = processor.process_directory(png_directory)