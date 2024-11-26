import os
import sys

from django.conf import settings
from dotenv import load_dotenv

from main.models import DocumentBatch, ProcessedDocument
from main.utils.embed_open import DocumentEmbedder


def test_document_embeddings():
    """Test document embedding functionality"""
    print("Starting test_document_embeddings...", file=sys.stderr)

    # Load environment variables
    load_dotenv()

    # Initialize the embedder (it will automatically get API key from env)
    try:
        embedder = DocumentEmbedder()
        print("DocumentEmbedder initialized", file=sys.stderr)
    except ValueError as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        return

    try:
        latest_batch = DocumentBatch.objects.latest("created_at")
        print(f"\nProcessing batch: {latest_batch.name}", file=sys.stderr)

        documents = ProcessedDocument.objects.filter(batch=latest_batch)
        print(f"Found {documents.count()} documents in batch", file=sys.stderr)

        if not documents:
            print("No documents found in the batch", file=sys.stderr)
            return

        texts = []
        metadata = []

        for doc in documents:
            print(f"Processing document: {doc.filename}", file=sys.stderr)
            text_content = doc.get_text_content()
            if text_content and text_content.strip():
                texts.append(text_content)
                metadata.append(
                    {
                        "id": str(doc.id),
                        "filename": doc.filename,
                        "batch_id": str(doc.batch.id),
                        "batch_name": doc.batch.name,
                        "status": doc.status,
                    }
                )

        if not texts:
            print("No valid text content found in documents", file=sys.stderr)
            return

        print(f"\nCreating embeddings for {len(texts)} documents...", file=sys.stderr)
        embeddings = embedder.create_batch_embeddings(texts)

        # Save embeddings
        output_dir = "media/embeddings"
        output_file = embedder.save_embeddings(embeddings, metadata, output_dir)
        print(f"\nEmbeddings saved to: {output_file}", file=sys.stderr)

        # Test search functionality
        print("\nTesting search functionality...", file=sys.stderr)
        embeddings_data = embedder.load_embeddings(output_file)

        test_queries = [
            "What are the building code requirements?",
            "Tell me about safety regulations",
            "What are the construction standards?",
        ]

        for query in test_queries:
            print(f"\nQuery: {query}", file=sys.stderr)
            results = embedder.search_documents(query, embeddings_data, top_k=3)

            print("\nTop 3 most relevant documents:", file=sys.stderr)
            for i, result in enumerate(results, 1):
                print(f"\n{i}. {result['metadata']['filename']}", file=sys.stderr)
                print(
                    f"   Similarity score: {result['similarity']:.4f}", file=sys.stderr
                )
                print(f"   Status: {result['metadata']['status']}", file=sys.stderr)

    except DocumentBatch.DoesNotExist:
        print("No document batches found", file=sys.stderr)
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        import traceback

        traceback.print_exc(file=sys.stderr)


# Run the test when executed in Django shell
test_document_embeddings()
