"""Embedding generation service using OpenAI."""

import asyncio
import logging
from typing import Any

from openai import AsyncOpenAI, RateLimitError

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating text embeddings using OpenAI."""

    def __init__(
        self,
        model: str = "text-embedding-3-small",
        batch_size: int = 100,
        max_retries: int = 3,
    ):
        """
        Initialize embedding service.

        Args:
            model: OpenAI embedding model to use
            batch_size: Maximum texts to embed in one API call
            max_retries: Maximum retry attempts for rate limiting
        """
        self.client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
        )
        self.model = model
        self.batch_size = batch_size
        self.max_retries = max_retries

    async def generate_embedding(self, text: str) -> list[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector

        Raises:
            Exception: If embedding generation fails after retries
        """
        embeddings = await self.generate_embeddings([text])
        return embeddings[0]

    async def generate_embeddings(
        self, texts: list[str], retry_count: int = 0
    ) -> list[list[float]]:
        """
        Generate embeddings for multiple texts with batching.

        Args:
            texts: List of texts to embed
            retry_count: Current retry attempt

        Returns:
            List of embedding vectors

        Raises:
            Exception: If embedding generation fails after max retries
        """
        if not texts:
            return []

        try:
            # Clean texts - remove empty strings and whitespace-only
            cleaned_texts = [text.strip() for text in texts if text.strip()]

            if not cleaned_texts:
                logger.warning("No valid texts to embed after cleaning")
                return []

            logger.info(
                f"Generating embeddings for {len(cleaned_texts)} texts "
                f"using model {self.model}"
            )

            response = await self.client.embeddings.create(
                model=self.model, input=cleaned_texts
            )

            embeddings = [item.embedding for item in response.data]

            logger.info(
                f"Successfully generated {len(embeddings)} embeddings "
                f"(dimension: {len(embeddings[0]) if embeddings else 0})"
            )

            return embeddings

        except RateLimitError as e:
            if retry_count < self.max_retries:
                # Exponential backoff: 2^retry_count seconds
                wait_time = 2**retry_count
                logger.warning(
                    f"Rate limit hit, retrying in {wait_time}s "
                    f"(attempt {retry_count + 1}/{self.max_retries})"
                )
                await asyncio.sleep(wait_time)
                return await self.generate_embeddings(texts, retry_count + 1)
            else:
                logger.error(
                    f"Max retries ({self.max_retries}) exceeded for rate limiting"
                )
                raise Exception(
                    f"Failed to generate embeddings after {self.max_retries} retries"
                ) from e

        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise

    async def generate_embeddings_batched(
        self, texts: list[str], show_progress: bool = True
    ) -> list[list[float]]:
        """
        Generate embeddings for large lists with automatic batching.

        Args:
            texts: List of texts to embed
            show_progress: Whether to log progress

        Returns:
            List of embedding vectors

        Raises:
            Exception: If any batch fails
        """
        all_embeddings = []
        total_batches = (len(texts) + self.batch_size - 1) // self.batch_size

        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]
            batch_num = i // self.batch_size + 1

            if show_progress:
                logger.info(
                    f"Processing batch {batch_num}/{total_batches} "
                    f"({len(batch)} texts)"
                )

            batch_embeddings = await self.generate_embeddings(batch)
            all_embeddings.extend(batch_embeddings)

            # Small delay between batches to avoid rate limiting
            if i + self.batch_size < len(texts):
                await asyncio.sleep(0.5)

        return all_embeddings

    async def embed_chunks(
        self, chunks: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Add embeddings to chunk dictionaries.

        Args:
            chunks: List of chunk dictionaries with 'content' field

        Returns:
            List of chunks with 'embedding' field added

        Raises:
            Exception: If embedding generation fails
        """
        texts = [chunk["content"] for chunk in chunks]

        logger.info(f"Generating embeddings for {len(texts)} chunks")

        embeddings = await self.generate_embeddings_batched(texts)

        # Add embeddings to chunks
        for chunk, embedding in zip(chunks, embeddings):
            chunk["embedding"] = embedding

        logger.info(f"Successfully embedded {len(chunks)} chunks")

        return chunks
