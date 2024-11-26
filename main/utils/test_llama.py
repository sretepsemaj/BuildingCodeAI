import os

from image_llama import LlamaImageProcessor


# ANSI color codes
class Colors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"


def test_image_processing():
    # Initialize the processor
    processor = LlamaImageProcessor()

    # Get the absolute path to the test image
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    test_image = os.path.join(base_dir, "static", "images", "png_files", "6Screenshot3.png")

    print(f"\n{Colors.HEADER}Testing Image Processing{Colors.ENDC}")
    print("=" * 50)

    # Process the image
    result = processor.convert_png_to_pdf(test_image)

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
        print(result["analysis"])

        # Print content length statistics
        content_length = len(result["content"])
        print(f"\n{Colors.HEADER}Content Statistics:{Colors.ENDC}")
        print("=" * 50)
        print(f"Total characters extracted: {content_length}")
        print(f"Approximate words: {len(result['content'].split())}")
        print(f"Number of sections: {result['content'].count('#')}")


if __name__ == "__main__":
    test_image_processing()
