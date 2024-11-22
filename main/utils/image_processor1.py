from dotenv import load_dotenv
import os
import base64
from typing import List, Dict
from openai import OpenAI
from PIL import Image
import io

class OpenAIImageProcessor:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        self.api_key = os.getenv('MYSK_API_KEY')
        if not self.api_key:
            raise ValueError("MYSK_API_KEY not found in environment variables")
        print(f"Using OpenAI API key: {self.api_key[:8]}...")
        
        # Initialize OpenAI client
        self.vision_client = OpenAI(api_key=self.api_key)

    def encode_image(self, image_path: str) -> str:
        """Encode image to base64 for API submission"""
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            raise Exception(f"Error encoding image: {str(e)}")

    def analyze_image(self, image_path: str) -> dict:
        """Analyze image using GPT-4 with vision capabilities"""
        try:
            if not os.path.exists(image_path):
                return {
                    'success': False,
                    'message': f'Image file not found: {image_path}',
                    'analysis': ''
                }

            print(f"\nAnalyzing image: {os.path.basename(image_path)}")
            print("1. Reading and encoding image...")
            # Encode the image
            base64_image = self.encode_image(image_path)
            print("2. Image encoded successfully")
            
            try:
                print("3. Making API request...")
                response = self.vision_client.chat.completions.create(
                    model="gpt-4o",  # Using GPT-4o which supports multimodal (text + image) input
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": """Please analyze this image in detail, focusing on:
1. Type of visualization (graph, chart, diagram, etc.)
2. Main components and their relationships
3. Key metrics, numbers, or data points
4. Any trends or patterns visible
5. Text content and labels
6. Color schemes and their significance
7. Overall purpose or message of the image

Please provide a comprehensive analysis with specific details and numbers where available."""
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/png;base64,{base64_image}",
                                        "detail": "high"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=16384  # GPT-4o supports up to 16,384 output tokens
                )
                print("4. Received API response")
                
                return {
                    'success': True,
                    'message': 'Image analyzed successfully',
                    'analysis': response.choices[0].message.content,
                    'filename': os.path.basename(image_path)
                }
                
            except Exception as api_error:
                error_msg = str(api_error)
                print(f"API Error: {error_msg}")
                if hasattr(api_error, 'response'):
                    print(f"Response details: {api_error.response}")
                    
                return {
                    'success': False,
                    'message': f'Error analyzing image with Vision API: {error_msg}',
                    'analysis': '',
                    'filename': os.path.basename(image_path)
                }
            
        except Exception as e:
            print(f"Error details: {str(e)}")
            if hasattr(e, 'response'):
                print(f"Response details: {e.response}")
            return {
                'success': False,
                'message': f'Error analyzing image with Vision API: {str(e)}',
                'analysis': '',
                'filename': os.path.basename(image_path)
            }

    def process_directory(self, directory_path: str) -> Dict:
        """Process all PNG files in a directory"""
        if not os.path.exists(directory_path):
            return {
                'success': False,
                'message': f'Directory not found: {directory_path}',
                'results': []
            }
            
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
            if filename.lower().endswith('.png'):
                total_files += 1
                png_files += 1
                file_path = os.path.join(directory_path, filename)
                result = self.analyze_image(file_path)
                results.append(result)
        
        if png_files == 0:
            return {
                'success': True,
                'message': f'No PNG files found in directory (found {total_files} other files)',
                'results': []
            }
            
        return {
            'success': True,
            'message': f'Processed {png_files} PNG files',
            'results': results
        }

# Example usage
if __name__ == "__main__":
    processor = OpenAIImageProcessor()
    png_directory = "/Users/aaronjpeters/PlumbingCodeAi/BuildingCodeai/main/static/images/png_files"
    results = processor.process_directory(png_directory)
    
    if results['success']:
        print(f"\n{results['message']}")
        for result in results['results']:
            print(f"\n--- Analysis for {result['filename']} ---")
            if result['success']:
                print(result['analysis'])
            else:
                print(f"Error: {result['message']}")
    else:
        print(f"Error: {results['message']}")
