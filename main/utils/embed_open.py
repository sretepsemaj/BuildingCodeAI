"""Module for creating and managing document embeddings using OpenAI's API."""

import json
import os
import time
from datetime import datetime
from typing import Any, Dict, List

import numpy as np
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables from .env file
load_dotenv()


class DocumentEmbedder:
    """A class for creating and managing document embeddings using OpenAI's API."""

    def __init__(self, api_key: str = None):
        """Initialize the DocumentEmbedder with OpenAI API key.

        Args:
            api_key: OpenAI API key. If None, tries to get from environment.

        Raises:
            ValueError: If no API key is provided and not found in environment.
        """
        if api_key is None:
            api_key = os.getenv("OPEN_API_KEY")
            if not api_key:
                raise ValueError("No API key provided and OPEN_API_KEY not found in environment")

        self.client = OpenAI(api_key=api_key)
        self.model = "text-embedding-ada-002"
        self.embedding_dim = 1536  # Dimension of ada-002 embeddings

    def get_embedding(self, text: str) -> list[float]:
        """Get embedding for a given text."""
        response = self.client.embeddings.create(input=text, model=self.model)
        return response.data[0].embedding

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for a list of texts.

        Args:
            texts: List of texts to get embeddings for.

        Returns:
            List of embeddings, one for each input text.
        """
        embeddings = []
        for text in texts:
            embeddings.append(self.get_embedding(text))
        return embeddings

    def create_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Create embeddings for a batch of texts.

        Args:
            texts: List of texts to create embeddings for.

        Returns:
            List of embeddings, one for each input text.
        """
        embeddings = []
        batch_size = 20  # Process in smaller batches to avoid rate limits

        for batch in self._batch_texts(texts, batch_size):
            batch_num = texts.index(batch[0]) // batch_size + 1
            total_batches = (len(texts) + batch_size - 1) // batch_size
            print(f"Processing batch {batch_num}/{total_batches}")

            for text in batch:
                embedding = self.get_embedding(text)
                if embedding:  # Only add if we got a valid embedding
                    embeddings.append(embedding)

            if texts.index(batch[0]) + batch_size < len(texts):
                print("Waiting 1 second before next batch...")
                time.sleep(1)  # Add delay between batches

        return embeddings

    def _batch_texts(self, texts: List[str], batch_size: int) -> List[List[str]]:
        """Split texts into batches.

        Args:
            texts: List of texts to split.
            batch_size: Size of each batch.

        Returns:
            List of text batches.
        """
        batches = []
        for i in range(0, len(texts), batch_size):
            batches.append(texts[i:i + batch_size])
        return batches

    def save_embeddings(
        self,
        embeddings: List[List[float]],
        metadata: List[Dict[str, Any]],
        output_file: str,
    ) -> None:
        """Save embeddings and metadata to a file."""
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(os.path.dirname(output_file), f"embeddings_{timestamp}.json")

        data = {
            "embeddings": embeddings,
            "metadata": metadata,
            "model": self.model,
            "dimension": self.embedding_dim,
            "created_at": timestamp,
        }

        with open(output_file, "w") as f:
            json.dump(data, f)

    def load_embeddings(self, filepath: str) -> Dict[str, Any]:
        """Load embeddings from a file.

        Args:
            filepath: Path to the file containing the embeddings.

        Returns:
            Dictionary containing the loaded embeddings and metadata.
        """
        with open(filepath, "r") as f:
            data = json.load(f)
        print(
            "Successfully loaded embeddings from file. "
            f"Found {len(data['embeddings'])} embeddings."
        )
        return data

    def compute_similarity(
        self, query_embedding: List[float], document_embeddings: List[List[float]]
    ) -> List[float]:
        """Compute cosine similarity between query and documents.

        Args:
            query_embedding: List of floats representing the query embedding vector.
            document_embeddings: List of lists of floats representing the document embedding vectors.

        Returns:
            List of floats representing the similarity scores.
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
