import os
import time

from image_open import OpenAIImageProcessor


def test_image_analysis():
    # Initialize the processor
    print("\n=== Testing OpenAI Image Analysis ===")
    try:
        processor = OpenAIImageProcessor()
        print("✓ Successfully initialized OpenAI Image Processor")
    except Exception as e:
        print(f"✗ Failed to initialize processor: {str(e)}")
        return

    # Test image path
    image_directory = (
        "/Users/aaronjpeters/PlumbingCodeAi/BuildingCodeai/main/static/images/png_files"
    )
    test_images = [
        f for f in os.listdir(image_directory) if f.endswith((".png", ".jpg", ".jpeg"))
    ]

    if not test_images:
        print("✗ No test images found in directory")
        return

    print(f"\nFound {len(test_images)} test images")

    for image_file in test_images:
        image_path = os.path.join(image_directory, image_file)
        print(f"\n--- Testing image: {image_file} ---")

        # Time the analysis
        start_time = time.time()

        try:
            result = processor.analyze_image(image_path)
            end_time = time.time()

            if result["success"]:
                print("✓ Analysis successful")
                print(f"Processing time: {end_time - start_time:.2f} seconds")
                print("\nAnalysis Results:")
                print("=" * 50)
                print(result["analysis"])
                print("=" * 50)
            else:
                print(f"✗ Analysis failed: {result['message']}")

        except Exception as e:
            print(f"✗ Error during analysis: {str(e)}")


if __name__ == "__main__":
    test_image_analysis()
