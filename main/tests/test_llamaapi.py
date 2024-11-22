import os
import unittest
import requests
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.conf import settings

class TestLlamaAPI(TestCase):
    def setUp(self):
        """Set up test environment variables and test file"""
        self.api_key = os.getenv('LAMA-API-KEY')
        self.base_url = 'https://api.cloud.llamaindex.ai/api'
        self.test_file_path = os.path.join(settings.BASE_DIR, 'main/tests/test_files/test.pdf')
        
        # Ensure test directory exists
        os.makedirs(os.path.dirname(self.test_file_path), exist_ok=True)
        
        # Create a simple test PDF file if it doesn't exist
        if not os.path.exists(self.test_file_path):
            with open(self.test_file_path, 'w') as f:
                f.write('Test content for PDF')

    def test_api_key_exists(self):
        """Test that the API key is properly set"""
        self.assertIsNotNone(self.api_key, "LAMA-API-KEY environment variable is not set")

    @patch('requests.post')
    def test_upload_file(self, mock_post):
        """Test file upload endpoint"""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'job_id': 'test_job_id'}
        mock_post.return_value = mock_response

        # Prepare the request
        url = f'{self.base_url}/parsing/upload'
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'accept': 'application/json'
        }
        
        with open(self.test_file_path, 'rb') as file:
            files = {'file': ('test.pdf', file, 'application/pdf')}
            response = requests.post(url, headers=headers, files=files)

        self.assertEqual(response.status_code, 200)
        self.assertIn('job_id', response.json())

    @patch('requests.get')
    def test_check_job_status(self, mock_get):
        """Test job status checking endpoint"""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'status': 'completed'}
        mock_get.return_value = mock_response

        # Test checking job status
        job_id = 'test_job_id'
        url = f'{self.base_url}/parsing/job/{job_id}'
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'accept': 'application/json'
        }
        
        response = requests.get(url, headers=headers)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'completed')

    @patch('requests.get')
    def test_get_results_markdown(self, mock_get):
        """Test getting results in markdown format"""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'content': '# Test Markdown'}
        mock_get.return_value = mock_response

        # Test getting results
        job_id = 'test_job_id'
        url = f'{self.base_url}/parsing/job/{job_id}/result/markdown'
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'accept': 'application/json'
        }
        
        response = requests.get(url, headers=headers)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('content', response.json())

    def tearDown(self):
        """Clean up test files"""
        if os.path.exists(self.test_file_path):
            os.remove(self.test_file_path)
        try:
            os.rmdir(os.path.dirname(self.test_file_path))
        except OSError:
            # Directory not empty or doesn't exist
            pass
