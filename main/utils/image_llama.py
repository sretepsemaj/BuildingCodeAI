import os
import tempfile
import time
from typing import Dict, List

import requests
from dotenv import load_dotenv
from llama_index.core import SimpleDirectoryReader
from llama_parse import LlamaParse
from PIL import Image


class LlamaImageProcessor:
    """A class for processing images using the Llama API."""

    def __init__(self) -> None:
        """Initialize the LlamaImageProcessor."""
        # Load environment variables
        load_dotenv()
        self.api_key = os.getenv("LAMA_API_KEY")
        print(f"Debug: API Key found: {'Yes' if self.api_key else 'No'}")
        if not self.api_key:
            raise ValueError("LAMA_API_KEY not found in environment variables")

        # Initialize LlamaParse
        self.parser = LlamaParse(api_key=self.api_key, result_type="markdown")

    def convert_png_to_pdf(self, image_path: str) -> Dict:
        """Convert PNG to PDF and process with LlamaParse"""
        print(f"\nDebug: Processing image: {image_path}")
        try:
            if not os.path.exists(image_path):
                print(f"Debug: File not found: {image_path}")
                return {"success": False, "message": f"File not found: {image_path}"}

            if not image_path.lower().endswith(".png"):
                print(f"Debug: Not a PNG file: {image_path}")
                return {"success": False, "message": "File is not a PNG image"}

            # Convert PNG to PDF
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_pdf:
                pdf_path = tmp_pdf.name
                print(f"Debug: Converting to PDF: {pdf_path}")
                image = Image.open(image_path)
                if image.mode == "RGBA":
                    image = image.convert("RGB")
                image.save(pdf_path, "PDF")

                try:
                    # Use SimpleDirectoryReader with LlamaParse
                    print("Debug: Processing with LlamaParse")
                    file_extractor = {".pdf": self.parser}
                    documents = SimpleDirectoryReader(
                        input_files=[pdf_path], file_extractor=file_extractor
                    ).load_data()

                    if documents and len(documents) > 0:
                        content = documents[0].text
                        print(f"Debug: Successfully extracted content, length: {len(content)}")

                        # Format the analysis content
                        analysis_content = []
                        analysis_content.append("### Processing Results")
                        analysis_content.append("**Status:** Completed")

                        if content.strip():
                            analysis_content.append("\n### Extracted Content")
                            analysis_content.append(content)
                        else:
                            analysis_content.append("\n### No Content Extracted")
                            analysis_content.append(
                                "The image was processed but no text content was found."
                            )
                            analysis_content.append("\nPossible reasons:")
                            analysis_content.append("- The image contains no text")
                            analysis_content.append("- The image quality is too low")
                            analysis_content.append("- The text format is not supported")

                        result = {
                            "success": True,
                            "message": "Successfully processed image",
                            "status": "completed",
                            "content": content,
                            "analysis": "\n".join(analysis_content),
                            "pdf_path": pdf_path,
                        }
                        print(f"Debug: Final result: {result}")
                        return result
                    else:
                        print("Debug: No documents returned from parser")
                        return {
                            "success": False,
                            "message": "No content extracted from image",
                            "status": "failed",
                            "content": "",
                            "analysis": "Failed to extract any content from the image",
                            "pdf_path": pdf_path,
                        }

                except Exception as parse_error:
                    print(f"Debug: Error during parsing: {str(parse_error)}")
                    return {
                        "success": False,
                        "message": f"Error during parsing: {str(parse_error)}",
                        "status": "error",
                        "content": "",
                        "analysis": f"Error during parsing: {str(parse_error)}",
                        "pdf_path": pdf_path,
                    }

        except Exception as e:
            print(f"Debug: Error in convert_png_to_pdf: {str(e)}")
            return {
                "success": False,
                "message": f"Error: {str(e)}",
                "status": "error",
                "content": "",
                "analysis": f"Error processing image: {str(e)}",
                "pdf_path": None,
            }

    def process_directory(self, directory_path: str) -> Dict[str, List]:
        """Process all PNG files in a directory"""
        print(f"\nDebug: Processing directory: {directory_path}")

        # Find all PNG files
        png_files = [f for f in os.listdir(directory_path) if f.lower().endswith(".png")]
        print(f"Debug: Found PNG files: {png_files}")

        results = []
        for filename in png_files:
            print(f"\nDebug: Processing file: {filename}")
            image_path = os.path.join(directory_path, filename)
            result = self.convert_png_to_pdf(image_path)

            # Restructure the result to match template expectations
            results.append(
                {
                    "filename": filename,
                    "success": result["success"],
                    "message": result["message"],
                    "analysis": result["analysis"],
                    "pdf_path": result.get("pdf_path"),
                }
            )
            print(f"Debug: File result: {result}")

        response = {
            "success": True,
            "message": f"Processed {len(png_files)} images",
            "results": results,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        print(f"\nDebug: Final response: {response}")
        return response


# Example usage:
if __name__ == "__main__":
    processor = LlamaImageProcessor()
    png_directory = "/Users/aaronjpeters/PlumbingCodeAi/BuildingCodeai/main/static/images/png_files"
    results = processor.process_directory(png_directory)
