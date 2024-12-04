import os
import re
import shutil
from pathlib import Path
from statistics import mean, stdev
from typing import Dict, List, Tuple

import pytesseract
from PIL import Image


def ensure_directories(base_dir: str) -> Dict[str, str]:
    """Ensure all required directories exist."""
    dirs = {
        "uploads": os.path.join(base_dir, "uploads"),
        "ocr": os.path.join(base_dir, "OCR"),
        "original": os.path.join(base_dir, "original"),
        "tables": os.path.join(base_dir, "tables"),
        "analytics": os.path.join(base_dir, "analytics"),
    }

    for dir_path in dirs.values():
        os.makedirs(dir_path, exist_ok=True)

    return dirs


def analyze_text_patterns(text: str) -> Tuple[bool, float]:
    """Analyze text patterns to detect table-like structures."""
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    if not lines:
        return False, 0.0

    # Pattern scores
    scores = []

    # 1. Check for measurement patterns
    measurement_pattern = r"\d+(?:\.\d+)?\s*(?:feet|foot|ft|inches|inch|mm|meters|m|\'|\")"
    measurements = sum(1 for line in lines if re.search(measurement_pattern, line, re.IGNORECASE))
    measurement_score = measurements / len(lines)
    scores.append(measurement_score * 2)  # Weight measurements heavily

    # 2. Analyze indentation patterns
    if len(lines) >= 3:
        indents = [len(line) - len(line.lstrip()) for line in lines]
        try:
            indent_consistency = 1.0 / (1.0 + stdev(indents))
            scores.append(indent_consistency)
        except (ValueError, ZeroDivisionError):
            scores.append(0.0)

    # 3. Check for consistent word spacing
    word_counts = [len(line.split()) for line in lines]
    if len(word_counts) >= 3:
        try:
            spacing_consistency = 1.0 / (1.0 + stdev(word_counts))
            scores.append(spacing_consistency)
        except (ValueError, ZeroDivisionError):
            scores.append(0.0)

    # 4. Look for numbered lists or bullet points
    numbered_pattern = r"^\s*(?:\d+\.|\(\d+\)|\w\.|\-|\•)\s"
    numbered_lines = sum(1 for line in lines if re.match(numbered_pattern, line))
    numbered_score = numbered_lines / len(lines)
    scores.append(numbered_score)

    # 5. Check for column-like structure
    spaces_pattern = r"\s{2,}"
    consistent_spaces = sum(1 for line in lines if len(re.findall(spaces_pattern, line)) >= 2)
    column_score = consistent_spaces / len(lines)
    scores.append(column_score * 2)  # Weight column structure heavily

    # Calculate final score
    final_score = mean(scores) if scores else 0.0
    return final_score > 0.3, final_score  # Threshold of 0.3 for table detection


def process_tables(image_path: str, output_dir: str) -> Dict:
    """Extract tables from image using text pattern analysis."""
    try:
        # Get text using OCR
        text_data = pytesseract.image_to_string(image_path)

        # Analyze text patterns
        is_table, confidence = analyze_text_patterns(text_data)

        if not is_table:
            return {
                "success": True,
                "table_path": None,
                "df_path": None,
                "error": f"No table patterns detected (confidence: {confidence:.2f})",
            }

        # If we detected a table, proceed with saving the data
        image_name = os.path.splitext(os.path.basename(image_path))[0]

        # Save the structured text
        table_path = os.path.join(output_dir, f"{image_name}_table.txt")
        with open(table_path, "w", encoding="utf-8") as f:
            f.write(text_data)

        # Try to extract structured data
        try:
            df_data = pytesseract.image_to_data(
                image_path,
                output_type=pytesseract.Output.DATAFRAME,
                config="--psm 11",
            )

            if len(df_data) > 0 and not df_data.empty:
                df_path = os.path.join(output_dir, f"{image_name}_data.csv")
                df_data.to_csv(df_path, index=False)

                return {
                    "success": True,
                    "table_path": table_path,
                    "df_path": df_path,
                    "error": None,
                    "confidence": confidence,
                }

        except Exception as e:
            pass

        return {
            "success": True,
            "table_path": table_path,
            "df_path": None,
            "error": f"Table detected with confidence {confidence:.2f}",
            "confidence": confidence,
        }

    except Exception as e:
        return {
            "success": False,
            "table_path": None,
            "df_path": None,
            "error": str(e),
            "confidence": 0.0,
        }


def process_image(image_path: str, output_path: str, tables_dir: str) -> Dict:
    """Process a single image with OCR and table detection."""
    try:
        # Open and process image
        with Image.open(image_path) as img:
            # Extract text using OCR
            text = pytesseract.image_to_string(img)

            # Save OCR text
            text_path = output_path.rsplit(".", 1)[0] + ".txt"
            with open(text_path, "w", encoding="utf-8") as f:
                f.write(text)

            # Process tables
            table_result = process_tables(image_path, tables_dir)

            return {
                "success": True,
                "text_path": text_path,
                "table_result": table_result,
                "error": None,
            }
    except Exception as e:
        return {
            "success": False,
            "text_path": None,
            "table_result": None,
            "error": str(e),
        }


def main():
    """Process images from uploads directory, save OCR results, and move originals."""
    # Setup directories
    base_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "media",
        "plumbing_code",
    )
    dirs = ensure_directories(base_dir)

    # Get list of files to process
    files = [
        f
        for f in os.listdir(dirs["uploads"])
        if f.lower().endswith((".png", ".jpg", ".jpeg", ".tiff", ".bmp"))
    ]

    results = {
        "processed": [],
        "failed": [],
        "stats": {"total": len(files), "success": 0, "failed": 0},
    }

    # Process each file
    for filename in files:
        input_path = os.path.join(dirs["uploads"], filename)
        output_path = os.path.join(dirs["ocr"], filename)
        tables_dir = dirs["tables"]

        try:
            # Process the image
            result = process_image(input_path, output_path, tables_dir)

            if result["success"]:
                # Only copy to analytics if it contains a table
                if result.get("table_result") and result["table_result"].get("table_path"):
                    analytics_path = os.path.join(dirs["analytics"], filename)
                    shutil.copy2(input_path, analytics_path)
                    analytics_location = analytics_path
                else:
                    analytics_location = None

                # Move original to original directory
                original_path = os.path.join(dirs["original"], filename)
                shutil.move(input_path, original_path)

                results["processed"].append(
                    {
                        "filename": filename,
                        "text_path": result["text_path"],
                        "table_result": result["table_result"],
                        "analytics_path": analytics_location,
                        "original_path": original_path,
                    }
                )
                results["stats"]["success"] += 1
            else:
                results["failed"].append(
                    {
                        "filename": filename,
                        "error": result["error"],
                    }
                )
                results["stats"]["failed"] += 1

        except Exception as e:
            results["failed"].append(
                {
                    "filename": filename,
                    "error": str(e),
                }
            )
            results["stats"]["failed"] += 1

    # Print summary
    print("\nProcessing Summary:")
    print(f"Total files: {results['stats']['total']}")
    print(f"Successfully processed: {results['stats']['success']}")
    print(f"Failed: {results['stats']['failed']}")

    if results["processed"]:
        print("\nSuccessfully Processed Files:")
        for item in results["processed"]:
            print(f"\nFile: {item['filename']}")
            print(f"OCR output: {item['text_path']}")
            print(f"Original moved to: {item['original_path']}")
            if item["analytics_path"]:
                print(f"Table found - Analytics copy: {item['analytics_path']}")
            if item["table_result"] and item["table_result"].get("table_path"):
                print(f"Table data: {item['table_result']['table_path']}")
                if item["table_result"].get("df_path"):
                    print(f"Structured data: {item['table_result']['df_path']}")
                print(f"Table confidence: {item['table_result'].get('confidence', 'N/A'):.2f}")

    if results["failed"]:
        print("\nFailed Files:")
        for item in results["failed"]:
            print(f"\nFile: {item['filename']}")
            print(f"Error: {item['error']}")

    return results


if __name__ == "__main__":
    main()
