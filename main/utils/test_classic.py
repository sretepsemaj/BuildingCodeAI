import os
import shutil
import unittest
from pathlib import Path
from PIL import Image
import numpy as np
from .doc_classic import DocClassicProcessor

class TestDocClassicProcessor(unittest.TestCase):
    def setUp(self):
        """Set up test environment before each test."""
        self.processor = DocClassicProcessor()
        self.test_dir = os.path.join(os.path.dirname(__file__), 'test_files')
        os.makedirs(self.test_dir, exist_ok=True)
        
        # Create a test image with text
        self.create_test_image()
        
        print("\n=== Starting new test ===")
    
    def tearDown(self):
        """Clean up after each test."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        print("=== Test completed ===\n")
    
    def create_test_image(self):
        """Create a test PNG image with text for OCR testing."""
        # Create a white image with sample text
        width, height = 400, 200
        image = Image.new('RGB', (width, height), color='white')
        
        # Save the test image
        self.test_image_path = os.path.join(self.test_dir, 'test.png')
        image.save(self.test_image_path)
        print(f"Created test image at: {self.test_image_path}")
    
    def test_initialization(self):
        """Test if the processor initializes correctly."""
        print("\nTesting initialization...")
        self.assertIsNotNone(self.processor)
        self.assertTrue(os.path.exists(self.processor.source_dir))
        self.assertTrue(os.path.exists(self.processor.destination_dir))
        print("Initialization successful")
    
    def test_process_single_image(self):
        """Test processing a single image."""
        print("\nTesting single image processing...")
        try:
            # Copy test image to source directory
            source_path = os.path.join(self.processor.source_dir, 'test.png')
            shutil.copy(self.test_image_path, source_path)
            
            # Process the image
            result = self.processor.process_image_to_text(source_path)
            
            # Verify results
            self.assertTrue(os.path.exists(result))
            with open(result, 'r', encoding='utf-8') as f:
                text = f.read()
                print(f"Extracted text from image: {text}")
            
            print("Single image processing successful")
        except Exception as e:
            print(f"Error in single image processing: {str(e)}")
            raise
    
    def test_batch_processing(self):
        """Test batch processing of multiple images."""
        print("\nTesting batch processing...")
        try:
            # Create multiple test images
            for i in range(3):
                source_path = os.path.join(self.processor.source_dir, f'test_{i}.png')
                shutil.copy(self.test_image_path, source_path)
            
            # Process all images
            results = self.processor.batch_process_directory()
            
            # Verify results
            self.assertIsInstance(results, list)
            self.assertTrue(all(os.path.exists(path) for path in results))
            
            # Print results
            for path in results:
                with open(path, 'r', encoding='utf-8') as f:
                    text = f.read()
                    print(f"\nProcessed {os.path.basename(path)}:")
                    print(f"Extracted text: {text}")
            
            print(f"Batch processing successful. Processed {len(results)} files")
        except Exception as e:
            print(f"Error in batch processing: {str(e)}")
            raise
    
    def test_cleanup(self):
        """Test cleanup functionality."""
        print("\nTesting cleanup...")
        try:
            # Create test files
            source_path = os.path.join(self.processor.source_dir, 'cleanup_test.png')
            shutil.copy(self.test_image_path, source_path)
            
            # Process and then cleanup
            self.processor.process_image_to_text(source_path)
            self.processor.cleanup_files(keep_original=False)
            
            # Verify cleanup
            self.assertFalse(os.path.exists(source_path))
            print("Cleanup successful")
        except Exception as e:
            print(f"Error in cleanup: {str(e)}")
            raise

if __name__ == '__main__':
    print("Starting DocClassicProcessor tests...")
    unittest.main(verbosity=2)