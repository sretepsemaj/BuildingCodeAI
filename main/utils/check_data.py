from typing import Dict, List, Optional

from main.models import PlumbingDocument, PlumbingImage, PlumbingTable


def get_document_data(doc_id: Optional[int] = None) -> List[Dict]:
    """Get document data in a format suitable for templates or checking.

    Args:
        doc_id: Optional ID to get specific document. If None, gets all documents.

    Returns:
        List of dictionaries containing document data
    """
    documents_data = []

    # Query documents
    if doc_id:
        documents = PlumbingDocument.objects.filter(id=doc_id)
    else:
        documents = PlumbingDocument.objects.all()

    for doc in documents:
        # Build document data
        doc_data = {
            "id": doc.id,
            "title": doc.title,
            "created_at": doc.created_at,
            "user": doc.user.username,
            "images": [],
            "tables": [],
            "json_paths": [],
        }

        # Get paths from JSON content
        if doc.json_content and "f" in doc.json_content:
            for item in doc.json_content["f"]:
                path_data = {
                    "page": item.get("i", "N/A"),
                    "image_path": item.get("o"),
                    "table_path": item.get("p"),
                    "text_content": item.get("t", ""),
                }
                doc_data["json_paths"].append(path_data)

        # Get images
        images = doc.images.all().order_by("page_number")
        for img in images:
            image_data = {
                "page": img.page_number,
                "file_path": img.image.name,
                "url": img.image.url if img.image else None,
            }
            doc_data["images"].append(image_data)

        # Get tables
        tables = doc.tables.all().order_by("page_number")
        for table in tables:
            table_data = {"page": table.page_number, "content": table.csv_content}
            doc_data["tables"].append(table_data)

        documents_data.append(doc_data)

    return documents_data


def print_database_contents():
    """Print a summary of all data in the database - useful for checking data"""
    documents_data = get_document_data()

    print("\n=== PLUMBING DOCUMENTS ===")
    print(f"Total documents: {len(documents_data)}")

    for doc in documents_data:
        print(f"\nDocument: {doc['title']}")
        print(f"Created at: {doc['created_at']}")
        print(f"User: {doc['user']}")

        print("\nPaths from JSON content:")
        for path in doc["json_paths"]:
            print(f"  Page {path['page']}:")
            if path["image_path"]:
                print(f"    Image: {path['image_path']}")
            if path["table_path"]:
                print(f"    Table: {path['table_path']}")

        print(f"\nImages in database ({len(doc['images'])}):")
        for img in doc["images"]:
            print(f"  - Page {img['page']}: {img['file_path']}")

        print(f"\nTables in database ({len(doc['tables'])}):")
        for table in doc["tables"]:
            print(f"  - Page {table['page']}: {table['content'][:100]}...")


# Example usage in a view:
"""
from django.shortcuts import render
from .utils.check_data import get_document_data

def document_view(request, doc_id=None):
    documents = get_document_data(doc_id)
    return render(request, 'your_template.html', {'documents': documents})
"""

if __name__ == "__main__":
    print_database_contents()
