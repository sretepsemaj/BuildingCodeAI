import json
import logging
import os
import shutil
from typing import Any, Dict

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_json_file(file_path: str) -> Dict[str, Any]:
    """Load and parse a JSON file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading JSON file {file_path}: {str(e)}")
        raise


def is_groq_empty(groq_data: list) -> bool:
    """Check if GROQ results are empty."""
    if not groq_data:
        return True

    # Check if all items in groq_data have empty content
    for item in groq_data:
        if item.get("groq_result", {}).get("content"):
            return False
    return True


def update_processed_json(processed_json_path: str, groq_json_path: str, output_path: str) -> None:
    """
    Update the processed JSON file with GROQ results or copy it if GROQ results are empty.

    Args:
        processed_json_path: Path to the original processed JSON file
        groq_json_path: Path to the GROQ results JSON file
        output_path: Path where the final JSON should be saved
    """
    try:
        # Load GROQ results first to check if they're empty
        groq_data = load_json_file(groq_json_path)

        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # If GROQ results are empty, just copy the original file
        if is_groq_empty(groq_data):
            shutil.copy2(processed_json_path, output_path)
            logger.info(f"GROQ results were empty. Copied original file to {output_path}")
            return

        # If GROQ has content, proceed with the update
        processed_data = load_json_file(processed_json_path)

        # Create a mapping of page numbers to GROQ results
        groq_results = {}
        for item in groq_data:
            page_num = item.get("page_num")
            if page_num and "groq_result" in item:
                groq_results[page_num] = item["groq_result"].get("content", "")

        # Update the text content in the processed JSON
        if "f" in processed_data:
            for item in processed_data["f"]:
                # Get the page number from the item
                page_num = item.get("i")
                if page_num in groq_results:
                    # Update the text content
                    item["t"] = groq_results[page_num]

        # Save the updated JSON
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(processed_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Successfully updated JSON with GROQ results and saved to {output_path}")

    except Exception as e:
        logger.error(f"Error updating JSON: {str(e)}")
        raise


def main():
    """Main function to process the files."""
    try:
        # Base paths
        base_dir = "/Users/aaronjpeters/PlumbingCodeAi/BuildingCodeai/media/plumbing_code"
        processed_dir = f"{base_dir}/json_processed"
        final_dir = f"{base_dir}/json_final"

        # Define the file paths for both chapters
        chapters = [
            {
                "processed": f"{processed_dir}/NYCP1CH.json",
                "groq": f"{final_dir}/NYCP1CH_groq.json",
                "output": f"{final_dir}/NYCP1CH_final.json",
            },
            {
                "processed": f"{processed_dir}/NYCP3CH.json",
                "groq": f"{final_dir}/NYCP3CH_groq.json",
                "output": f"{final_dir}/NYCP3CH_final.json",
            },
        ]

        # Process each chapter
        for chapter in chapters:
            update_processed_json(chapter["processed"], chapter["groq"], chapter["output"])

    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        raise


if __name__ == "__main__":
    main()
