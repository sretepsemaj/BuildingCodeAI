import os

from image_groq import GroqImageProcessor


# ANSI color codes
class Colors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"


def test_groq_processing():
    # Initialize the processor
    processor = GroqImageProcessor()

    # Get the absolute path to the test image
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    test_image = os.path.join(
        base_dir, "static", "images", "png_files", "6Screenshot3.png"
    )

    print(f"\n{Colors.HEADER}Testing Groq Image Processing{Colors.ENDC}")
    print("=" * 50)

    try:
        # Check if test image exists
        if not os.path.exists(test_image):
            print(
                f"{Colors.FAIL}Error: Test image not found at {test_image}{Colors.ENDC}"
            )
            print(
                f"{Colors.WARNING}Make sure you have placed '6Screenshot3.png' in the static/images/png_files/ directory{Colors.ENDC}"
            )
            return

        # Process the image
        print(f"{Colors.OKBLUE}Processing image: {test_image}{Colors.ENDC}")
        with open(test_image, "rb") as f:
            image_data = f.read()
            print(f"{Colors.OKBLUE}Image size: {len(image_data)} bytes{Colors.ENDC}")
            result = processor.process_image(image_data)

        # Print the result
        print(f"\n{Colors.BOLD}Processing Result:{Colors.ENDC}")
        print("=" * 50)
        success_color = Colors.OKGREEN if result["success"] else Colors.FAIL
        print(f"{success_color}Success:{Colors.ENDC} {result['success']}")
        print(f"{Colors.OKBLUE}Message:{Colors.ENDC} {result['message']}")
        print(f"{Colors.OKBLUE}Status:{Colors.ENDC} {result['status']}")

        if result["success"]:
            print(f"\n{Colors.BOLD}Content Analysis:{Colors.ENDC}")
            print("=" * 50)

            if "content" in result:
                content = result["content"]
                print(f"\n{Colors.HEADER}Extracted Content:{Colors.ENDC}")
                print("-" * 50)
                print(content)

                # Print content statistics
                print(f"\n{Colors.HEADER}Content Statistics:{Colors.ENDC}")
                print("-" * 50)
                print(f"Total characters: {len(content)}")
                print(f"Approximate words: {len(content.split())}")
                print(f"Number of sections: {content.count('#')}")
                print(
                    f"Number of tables: {content.count('|') // 2}"
                )  # Rough estimate of table rows

                # Print table information if available
                if "table_summary" in result:
                    print(f"\n{Colors.HEADER}Table Summary:{Colors.ENDC}")
                    print("-" * 50)
                    print(result["table_summary"])

            # Print PDF path if available
            if "pdf_path" in result:
                print(f"\n{Colors.HEADER}Generated PDF:{Colors.ENDC}")
                print("-" * 50)
                print(f"PDF saved at: {result['pdf_path']}")

    except Exception as e:
        print(f"\n{Colors.FAIL}Error during processing:{Colors.ENDC}")
        print(f"Error: {str(e)}")


if __name__ == "__main__":
    test_groq_processing()
