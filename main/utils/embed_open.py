"""Module for creating and managing document embeddings using OpenAI's API."""

import json
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
from django.conf import settings
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables from .env file
load_dotenv()


class DocumentEmbedder:
    """A class for creating and managing document embeddings using OpenAI's API."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the DocumentEmbedder with OpenAI API key.

        Args:
            api_key: OpenAI API key. If None, tries to get from environment.

        Raises:
            ValueError: If no API key is provided and not found in environment.
        """
        if api_key:
            self.api_key = api_key
        else:
            self.api_key = os.getenv("OPEN_API_KEY")
            if not self.api_key:
                raise ValueError("No API key provided and OPEN_API_KEY not found in environment")

        self.client = OpenAI(api_key=api_key)
        self.model = "text-embedding-ada-002"
        self.embedding_dim = 1536  # Dimension of ada-002 embeddings
        self.chunk_size = 4097  # Maximum chunk size for text embedding

    def get_embedding(self, text: str) -> List[float]:
        """Get embedding for a given text."""
        response = self.client.embeddings.create(input=text, model=self.model)
        return response.data[0].embedding

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for multiple texts.

        Args:
            texts: List of texts to get embeddings for.

        Returns:
            List of embeddings, one for each input text.
        """
        embeddings = []
        for text in texts:
            embedding = self.get_embedding(text)
            embeddings.append(embedding)
        return embeddings

    def get_embeddings_batch(
        self, texts: List[str], batch_size: int = 20, delay: float = 0.1
    ) -> List[List[float]]:
        """Get embeddings for texts in batches to handle rate limits.

        Args:
            texts: List of texts to get embeddings for.
            batch_size: Number of texts to process in each batch.
            delay: Delay between batches in seconds.

        Returns:
            List of embeddings, one for each input text.
        """
        embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            batch_embeddings = self.get_embeddings(batch)
            embeddings.extend(batch_embeddings)
            if i + batch_size < len(texts):
                time.sleep(delay)
        return embeddings

    def create_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Create embeddings for a batch of texts.

        Args:
            texts: List of texts to get embeddings for.

        Returns:
            List of embeddings, one for each input text.
        """
        embeddings = []
        for text in texts:
            embedding = self.get_embedding(text)
            embeddings.append(embedding)
        return embeddings

    def process_text_batch(
        self, texts: List[str], batch_size: int = 20, delay: float = 0.1
    ) -> List[List[float]]:
        """Process a batch of texts to create embeddings.

        Args:
            texts: List of texts to process.
            batch_size: Number of texts to process in each batch.
            delay: Delay between batches in seconds.

        Returns:
            List of embeddings, one for each input text.
        """
        embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            batch_embeddings = self.create_batch_embeddings(batch)
            embeddings.extend(batch_embeddings)
            if i + batch_size < len(texts):
                time.sleep(delay)
        return embeddings

    def _batch_texts(self, texts, batch_size):
        """Split texts into batches.

        Args:
            texts: List of texts to split into batches.
            batch_size: Size of each batch.

        Returns:
            List of batches, where each batch is a list of texts.
        """
        batches = []
        for i in range(0, len(texts), batch_size):
            batches.append(texts[i : i + batch_size])
        return batches

    def save_embeddings(self, embeddings, metadata, output_dir, filename="embeddings.json"):
        """Save embeddings and metadata to a JSON file.

        Args:
            embeddings: List of embeddings to save.
            metadata: List of metadata for each embedding.
            output_dir: Directory to save the file in.
            filename: Name of the output file.

        Returns:
            Path to the saved file.
        """
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, filename)

        data = {
            "embeddings": embeddings,
            "metadata": metadata,
            "created_at": datetime.now().isoformat(),
        }

        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)

        return output_path

    def load_embeddings(self, filepath: str) -> Dict[str, Any]:
        """Load embeddings from a file.

        Args:
            filepath: Path to the embeddings file.

        Returns:
            Dictionary containing embeddings and metadata.
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")

        with open(filepath) as f:
            data = json.load(f)

        return data

    def compute_similarity(
        self, query_embedding: List[float], document_embeddings: List[List[float]]
    ) -> List[float]:
        """Compute cosine similarity between query and documents.

        Args:
            query_embedding: Query embedding vector.
            document_embeddings: Document embedding vectors.

        Returns:
            List of similarity scores.
        """
        query_embedding = np.array(query_embedding)
        document_embeddings = np.array(document_embeddings)

        # Normalize the embeddings
        query_norm = np.linalg.norm(query_embedding)
        doc_norms = np.linalg.norm(document_embeddings, axis=1)

        # Compute cosine similarity
        if query_norm > 0 and np.all(doc_norms > 0):
            query_normalized = query_embedding / query_norm
            docs_normalized = document_embeddings / doc_norms[:, np.newaxis]
            similarities = np.dot(docs_normalized, query_normalized)
            return similarities.tolist()
        return [0.0] * len(document_embeddings)

    def search_documents(
        self, query: str, embeddings_data: Dict[str, Any], top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Search for most similar documents given a query.

        Args:
            query: The query text to search for.
            embeddings_data: Dictionary containing the embeddings and metadata.
            top_k: Number of top results to return.

        Returns:
            List of dictionaries containing the metadata and similarity scores for the top results.
        """
        # Create embedding for the query
        query_embedding = self.get_embedding(query)

        # Get document embeddings and metadata
        document_embeddings = embeddings_data["embeddings"]
        metadata = embeddings_data["metadata"]

        # Compute similarities
        similarities = self.compute_similarity(query_embedding, document_embeddings)

        # Sort documents by similarity
        results = []
        for idx, similarity in enumerate(similarities):
            results.append({"metadata": metadata[idx], "similarity": similarity})

        # Sort by similarity score in descending order
        results.sort(key=lambda x: x["similarity"], reverse=True)

        return results[:top_k]

    def load_file(self, file_path: str) -> str:
        """Load a file and return its embedding.

        Args:
            file_path: Path to the file to load.

        Returns:
            Embedding of the file content as a string, or None if file doesn't exist.
        """
        # Check if file exists
        if not os.path.exists(file_path):
            return None

        # Read file content
        with open(file_path) as f:
            content = f.read()

        # Get embeddings
        response = self.client.embeddings.create(input=content, model=self.model)
        return response.data[0].embedding

    def load_document(self, document) -> List[List[float]]:
        """Load a document and return its embeddings.

        Args:
            document: Document object containing the text path.

        Returns:
            List of embeddings for each chunk of the document.
        """
        # Extract text from the document
        text_path = os.path.join(settings.MEDIA_ROOT, document.text_path.lstrip("/"))
        with open(text_path) as f:
            text = f.read()

        # Split text into chunks for embedding
        text_chunks = [text[i : i + self.chunk_size] for i in range(0, len(text), self.chunk_size)]

        # Get embeddings for each chunk
        embeddings = []
        for chunk in text_chunks:
            embedding = self.get_embedding(chunk)
            embeddings.append(embedding)

        return embeddings
