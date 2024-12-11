import base64
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

from django.conf import settings
from groq import Groq

logger = logging.getLogger("main.utils.image_groq")


class GroqImageProcessor:
    """Processor class for analyzing images using Groq AI API."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the processor with optional API key."""
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY environment variable is required")
        self.client = Groq(api_key=self.api_key)

    def analyze_image(self, image_path: str) -> str:
        """
        Analyze an image using Groq AI and return the description.

        Args:
            image_path: Path to the image file to analyze

        Returns:
            String containing the AI's description of the image
        """
        try:
            # Read and encode image
            with open(image_path, "rb") as image_file:
                image_data = base64.b64encode(image_file.read()).decode()

            # Create prompt with image
            prompt = (
                "You are an expert at analyzing plumbing code diagrams and images. "
                "Please describe what you see in this image, focusing on plumbing-related details. "
                "Be specific about pipe configurations, fixtures, and measurements if visible."
            )

            # Send request to Groq
            completion = self.client.chat.completions.create(
                model="mixtral-8x7b-32768",
                messages=[{"role": "user", "content": f"{prompt}\n\nImage: {image_data}"}],
                temperature=0.7,
                max_tokens=500,
            )

            # Return the generated description
            return completion.choices[0].message.content

        except Exception as e:
            logger.error(f"Error analyzing image {image_path}: {str(e)}")
            return ""


if __name__ == "__main__":
    # Use the image path provided
    image_path = "media/plumbing_code/optimizer/NYCP3ch_4pg.jpg"

    # Make sure we're in the right directory
    os.chdir(str(Path(__file__).resolve().parent.parent.parent))

    # Analyze the image
    try:
        processor = GroqImageProcessor()
        result = processor.analyze_image(image_path)
        print("\nAnalysis Result:")
        print(result)
    except Exception as e:
        print(f"Error analyzing image: {str(e)}")
