import os
import unittest
import base64
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.conf import settings
from openai import OpenAI
from main.utils.image_processor import LlamaImageProcessor

class TestOpenAIAPI(TestCase):
    def setUp(self):
        """Set up test environment variables and test files"""
        self.api_key = os.getenv('OPEN_API_KEY')
        self.test_image_path = os.path.join(settings.BASE_DIR, 'main/tests/test_files/test_image.png')
        
        # Ensure test directory exists
        os.makedirs(os.path.dirname(self.test_image_path), exist_ok=True)
        
        # Create a simple test PNG file if it doesn't exist
        if not os.path.exists(self.test_image_path):
            from PIL import Image
            import numpy as np
            # Create a simple 100x100 test image
            arr = np.zeros([100, 100, 3], dtype=np.uint8)
            arr[:50, :50] = [255, 0, 0]  # Red square
            img = Image.fromarray(arr)
            img.save(self.test_image_path)

    def test_api_key_exists(self):
        """Test that the OpenAI API key is properly set"""
        self.assertIsNotNone(self.api_key, "OPEN_API_KEY environment variable is not set")

    def test_api_key_valid_format(self):
        """Test that the API key follows OpenAI's format"""
        self.assertTrue(self.api_key.startswith('sk-'), "OpenAI API key should start with 'sk-'")
        self.assertTrue(len(self.api_key) > 20, "OpenAI API key seems too short")

    @patch('main.utils.image_processor.OpenAIClient')
    def test_gpt4_vision_endpoint(self, mock_openai_client):
        """Test GPT-4 Vision API endpoint"""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Test analysis of image"))]
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_client.return_value = mock_client

        # Initialize processor
        processor = LlamaImageProcessor()
        
        # Test image analysis
        result = processor.analyze_with_gpt4_vision(self.test_image_path)
        
        self.assertTrue(result['success'])
        self.assertIn('analysis', result)
        
        # Verify the API was called with correct parameters
        mock_client.chat.completions.create.assert_called_once()
        call_args = mock_client.chat.completions.create.call_args[1]
        self.assertEqual(call_args['model'], 'gpt-4-vision-preview')
        self.assertEqual(len(call_args['messages']), 1)
        self.assertIn('image_url', call_args['messages'][0]['content'][1])

    def test_image_encoding(self):
        """Test image encoding for API submission"""
        processor = LlamaImageProcessor()
        
        # Test encoding
        encoded_image = processor.encode_image(self.test_image_path)
        
        self.assertIsInstance(encoded_image, str)
        self.assertTrue(len(encoded_image) > 0)
        
        # Verify it's valid base64
        try:
            decoded = base64.b64decode(encoded_image)
            self.assertTrue(len(decoded) > 0)
        except Exception as e:
            self.fail(f"Failed to decode base64 image: {str(e)}")

    @patch('main.utils.image_processor.OpenAIClient')
    def test_error_handling(self, mock_openai_client):
        """Test error handling in GPT-4 Vision API calls"""
        # Mock error response
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        mock_openai_client.return_value = mock_client

        # Initialize processor
        processor = LlamaImageProcessor()
        
        # Test error handling
        result = processor.analyze_with_gpt4_vision(self.test_image_path)
        
        self.assertFalse(result['success'])
        self.assertIn('Error analyzing image with GPT-4 Vision', result['message'])
        self.assertEqual(result['analysis'], '')

    def test_invalid_image_path(self):
        """Test handling of invalid image paths"""
        processor = LlamaImageProcessor()
        
        result = processor.analyze_with_gpt4_vision('nonexistent_image.png')
        
        self.assertFalse(result['success'])
        self.assertEqual(result['message'], 'Image file not found: nonexistent_image.png')
        self.assertEqual(result['analysis'], '')

    def tearDown(self):
        """Clean up test files"""
        if os.path.exists(self.test_image_path):
            os.remove(self.test_image_path)
