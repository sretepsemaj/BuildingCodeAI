import os
from openai import OpenAI
import numpy as np
from typing import List, Dict, Any
import json
from datetime import datetime
import time
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class DocumentEmbedder:
    def __init__(self, api_key: str = None):
        """Initialize the DocumentEmbedder with OpenAI API key."""
        if api_key is None:
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                raise ValueError("No API key provided and OPENAI_API_KEY not found in environment variables")
        
        self.client = OpenAI(api_key=api_key)
        self.model = "text-embedding-ada-002"
        self.embedding_dim = 1536  # Dimension of ada-002 embeddings

    def create_embedding(self, text: str) -> List[float]:
        """Create an embedding for a single text using OpenAI's API."""
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                response = self.client.embeddings.create(
                    model=self.model,
                    input=text
                )
                return response.data[0].embedding
            except Exception as e:
                print(f"Error creating embedding (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    print(f"Waiting {retry_delay} seconds before retrying...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    print("Max retries exceeded. Skipping this text.")
                    return []

    def create_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Create embeddings for a batch of texts."""
        embeddings = []
        batch_size = 20  # Process in smaller batches to avoid rate limits
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            print(f"Processing batch {i//batch_size + 1}/{(len(texts) + batch_size - 1)//batch_size}")
            
            for text in batch:
                embedding = self.create_embedding(text)
                if embedding:  # Only add if we got a valid embedding
                    embeddings.append(embedding)
            
            if i + batch_size < len(texts):
                print("Waiting 1 second before next batch...")
                time.sleep(1)  # Add delay between batches
        
        return embeddings

    def save_embeddings(self, embeddings: List[List[float]], metadata: List[Dict[str, Any]], output_dir: str):
        """Save embeddings and metadata to a file."""
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(output_dir, f"embeddings_{timestamp}.json")
        
        data = {
            "embeddings": embeddings,
            "metadata": metadata,
            "model": self.model,
            "dimension": self.embedding_dim,
            "created_at": timestamp
        }
        
        with open(output_file, 'w') as f:
            json.dump(data, f)
        
        return output_file

    def load_embeddings(self, filepath: str) -> Dict[str, Any]:
        """Load embeddings from a file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        return data

    def compute_similarity(self, query_embedding: List[float], document_embeddings: List[List[float]]) -> List[float]:
        """Compute cosine similarity between query and documents."""
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

    def search_documents(self, query: str, embeddings_data: Dict[str, Any], top_k: int = 5) -> List[Dict[str, Any]]:
        """Search for most similar documents given a query."""
        # Create embedding for the query
        query_embedding = self.create_embedding(query)
        
        # Get document embeddings and metadata
        document_embeddings = embeddings_data["embeddings"]
        metadata = embeddings_data["metadata"]
        
        # Compute similarities
        similarities = self.compute_similarity(query_embedding, document_embeddings)
        
        # Sort documents by similarity
        results = []
        for idx, similarity in enumerate(similarities):
            results.append({
                "metadata": metadata[idx],
                "similarity": similarity
            })
        
        # Sort by similarity score in descending order
        results.sort(key=lambda x: x["similarity"], reverse=True)
        
        return results[:top_k]
