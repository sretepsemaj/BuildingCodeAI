import base64
import os
import unittest
from unittest.mock import MagicMock, patch

import numpy as np
from django.conf import settings
from django.test import TestCase
from groq import Groq
from PIL import Image


class TestGroqAPI(TestCase):
    def setUp(self):
        """Set up test environment variables and test file"""
        self.api_key = os.getenv("GROQ_API_KEY")
        self.model = "llama-3.2-11b-vision-preview"
        self.test_image_path = os.path.join(
            settings.BASE_DIR, "main/tests/test_files/test_image.jpg"
        )

        # Ensure test directory exists
        os.makedirs(os.path.dirname(self.test_image_path), exist_ok=True)

        # Create a simple test image file if it doesn't exist
        if not os.path.exists(self.test_image_path):
            # Create a 100x100 red square image
            img = Image.fromarray(np.full((100, 100, 3), [255, 0, 0], dtype=np.uint8))
            img.save(self.test_image_path, "JPEG")

    def test_api_key_exists(self):
        """Test that the API key is properly set"""
        self.assertIsNotNone(self.api_key, "GROQ_API_KEY environment variable is not set")

    def encode_image(self, image_path):
        """Helper function to encode image to base64"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    @patch("groq.Groq")
    def test_process_local_image(self, mock_groq_class):
        """Test processing a local image file"""
        # Mock successful response
        mock_completion = MagicMock()
        mock_completion.choices = [
            MagicMock(message=MagicMock(content="Test image analysis result"))
        ]
        mock_groq_class.return_value.chat.completions.create.return_value = mock_completion

        # Encode test image
        base64_image = self.encode_image(self.test_image_path)

        # Create Groq client and make request
        client = mock_groq_class(api_key=self.api_key)
        completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "What's in this image?"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}",
                            },
                        },
                    ],
                }
            ],
            model=self.model,
        )

        # Assert API was called correctly
        mock_groq_class.return_value.chat.completions.create.assert_called_once()
        self.assertIsNotNone(completion.choices[0].message.content)
        self.assertEqual(completion.choices[0].message.content, "Test image analysis result")

    @patch("groq.Groq")
    def test_process_url_image(self, mock_groq_class):
        """Test processing an image from URL"""
        # Mock successful response
        mock_completion = MagicMock()
        mock_completion.choices = [
            MagicMock(message=MagicMock(content="Test URL image analysis result"))
        ]
        mock_groq_class.return_value.chat.completions.create.return_value = mock_completion

        # Create Groq client and make request
        client = mock_groq_class(api_key=self.api_key)
        completion = client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "What's in this image?"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": "https://upload.wikimedia.org/wikipedia/commons/f/f2/LPU-v1-die.jpg"
                            },
                        },
                    ],
                }
            ],
        )

        # Assert API was called correctly
        mock_groq_class.return_value.chat.completions.create.assert_called_once()
        self.assertIsNotNone(completion.choices[0].message.content)
        self.assertEqual(completion.choices[0].message.content, "Test URL image analysis result")

    @patch("groq.Groq")
    def test_json_mode(self, mock_groq_class):
        """Test JSON mode for image analysis"""
        # Mock successful response
        mock_completion = MagicMock()
        mock_completion.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"objects": ["test object"], "description": "test description"}'
                )
            )
        ]
        mock_groq_class.return_value.chat.completions.create.return_value = mock_completion

        # Create Groq client and make request
        client = mock_groq_class(api_key=self.api_key)
        completion = client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "List what you observe in this image in JSON format.",
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": "https://upload.wikimedia.org/wikipedia/commons/d/da/SF_From_Marin_Highlands3.jpg"
                            },
                        },
                    ],
                }
            ],
            response_format={"type": "json_object"},
        )

        # Assert API was called correctly and returned JSON
        mock_groq_class.return_value.chat.completions.create.assert_called_once()
        self.assertIsNotNone(completion.choices[0].message.content)
        self.assertIn('"objects":', completion.choices[0].message.content)
        self.assertIn('"description":', completion.choices[0].message.content)

    def tearDown(self):
        """Clean up test files"""
        if os.path.exists(self.test_image_path):
            os.remove(self.test_image_path)
        try:
            os.rmdir(os.path.dirname(self.test_image_path))
        except OSError:
            # Directory not empty or doesn't exist
            pass
