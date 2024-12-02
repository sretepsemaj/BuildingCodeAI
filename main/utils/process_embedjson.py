"""Script for creating embeddings from plumbing code JSON files with best practices."""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from embed_open import DocumentEmbedder
from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("embedding_process.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class PlumbingCodeEmbedder:
    """Class for creating and managing embeddings for plumbing code documents."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize with document embedder and configuration."""
        self.embedder = DocumentEmbedder(api_key)
        self.chunk_size = 1500  # Target words per chunk
        self.batch_size = 20
        self.delay = 0.1

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content."""
        # Remove excessive whitespace
        text = " ".join(text.split())
        # Normalize newlines
        text = text.replace("\n\n", "\n")
        return text

    def _create_chunks(self, text: str, section_id: str, title: str) -> List[Dict[str, Any]]:
        """Create meaningful chunks from text while preserving context."""
        words = text.split()
        chunks = []

        for i in range(0, len(words), self.chunk_size):
            chunk_words = words[i : i + self.chunk_size]
            chunk_text = " ".join(chunk_words)

            # Add context at the start of each chunk
            if i > 0:
                chunk_text = f"{title} (Section {section_id} continued): {chunk_text}"
            else:
                chunk_text = f"{title} (Section {section_id}): {chunk_text}"

            chunks.append({"text": chunk_text, "start_idx": i, "end_idx": i + len(chunk_words)})

        return chunks

    def process_json_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Process a single JSON file and prepare chunks for embedding."""
        try:
            with open(file_path, "r") as f:
                data = json.load(f)

            chunks = []
            chapter_info = data.get("m", {})
            chapter_num = chapter_info.get("c", "")
            chapter_title = chapter_info.get("ct", "")

            # Process sections
            for section in data.get("s", []):
                section_id = section.get("i", "")
                section_text = section.get("t", "")

                if section_text:
                    cleaned_text = self._clean_text(section_text)
                    section_chunks = self._create_chunks(cleaned_text, section_id, chapter_title)

                    for chunk in section_chunks:
                        chunks.append(
                            {
                                "chapter": chapter_num,
                                "section": section_id,
                                "title": chapter_title,
                                "text": chunk["text"],
                                "source_file": os.path.basename(file_path),
                                "ocr_paths": [f["o"] for f in data.get("f", [])],
                            }
                        )

            return chunks

        except Exception as e:
            logger.error(f"Error processing file {file_path}: {str(e)}")
            raise

    async def create_embeddings(self, input_dir: str, output_file: str):
        """Create embeddings for all JSON files in the directory."""
        try:
            # Get all JSON files
            json_files = [f for f in os.listdir(input_dir) if f.endswith(".json")]
            all_chunks = []

            # Process each file
            for file_name in tqdm(json_files, desc="Processing JSON files"):
                file_path = os.path.join(input_dir, file_name)
                chunks = self.process_json_file(file_path)
                all_chunks.extend(chunks)

            # Create embeddings in batches
            embeddings = []
            for i in tqdm(range(0, len(all_chunks), self.batch_size), desc="Creating embeddings"):
                batch = all_chunks[i : i + self.batch_size]
                batch_texts = [chunk["text"] for chunk in batch]

                try:
                    batch_embeddings = self.embedder.get_embeddings_batch(
                        batch_texts, batch_size=self.batch_size, delay=self.delay
                    )

                    for chunk, embedding in zip(batch, batch_embeddings):
                        embeddings.append(
                            {
                                "id": f"{chunk['source_file']}-{chunk['section']}",
                                "text": chunk["text"],
                                "embedding": embedding,
                                "metadata": {
                                    "chapter": chunk["chapter"],
                                    "section": chunk["section"],
                                    "title": chunk["title"],
                                    "source_file": chunk["source_file"],
                                    "ocr_paths": chunk["ocr_paths"],
                                },
                            }
                        )

                    # Save progress periodically
                    if len(embeddings) % 100 == 0:
                        self._save_embeddings(embeddings, output_file)

                except Exception as e:
                    logger.error(f"Error in batch starting at index {i}: {str(e)}")
                    # Save progress before raising error
                    self._save_embeddings(embeddings, output_file)
                    raise

            # Save final results
            self._save_embeddings(embeddings, output_file)
            logger.info(f"Successfully created embeddings for {len(embeddings)} chunks")

        except Exception as e:
            logger.error(f"Error in create_embeddings: {str(e)}")
            raise

    def _save_embeddings(self, embeddings: List[Dict[str, Any]], output_file: str):
        """Save embeddings with metadata to file."""
        output_data = {
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "model": self.embedder.model,
                "version": "1.0",
                "num_embeddings": len(embeddings),
            },
            "embeddings": embeddings,
        }

        # Save with temporary file to prevent corruption
        temp_file = output_file + ".tmp"
        try:
            with open(temp_file, "w") as f:
                json.dump(output_data, f, indent=2)
            os.replace(temp_file, output_file)
        except Exception as e:
            if os.path.exists(temp_file):
                os.remove(temp_file)
            raise

    def search_embeddings(
        self, query: str, embeddings_file: str, top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Search for most relevant sections given a query."""
        try:
            # Load embeddings
            with open(embeddings_file, "r") as f:
                data = json.load(f)

            embeddings_data = {
                "embeddings": [np.array(e["embedding"]) for e in data["embeddings"]],
                "metadata": [e["metadata"] for e in data["embeddings"]],
                "texts": [e["text"] for e in data["embeddings"]],
            }

            # Get query embedding
            query_embedding = self.embedder.get_embedding(query)

            # Calculate similarities
            similarities = self.embedder.compute_similarity(
                query_embedding, embeddings_data["embeddings"]
            )

            # Get top results
            top_indices = np.argsort(similarities)[-top_k:][::-1]

            results = []
            for idx in top_indices:
                results.append(
                    {
                        "text": embeddings_data["texts"][idx],
                        "metadata": embeddings_data["metadata"][idx],
                        "similarity": float(similarities[idx]),
                    }
                )

            return results

        except Exception as e:
            logger.error(f"Error in search_embeddings: {str(e)}")
            raise


def main():
    """Main function to run the embedding process."""
    try:
        # Initialize embedder
        embedder = PlumbingCodeEmbedder()

        # Define paths
        input_dir = (
            "/Users/aaronjpeters/PlumbingCodeAi/BuildingCodeai/main/media/"
            "plumbing_code/optimized/json"
        )
        output_file = (
            "/Users/aaronjpeters/PlumbingCodeAi/BuildingCodeai/main/media/"
            "plumbing_code/optimized/embeddings.json"
        )

        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        # Create embeddings
        asyncio.run(embedder.create_embeddings(input_dir, output_file))

        logger.info("Embedding process completed successfully")

    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        raise


if __name__ == "__main__":
    main()
