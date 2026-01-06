"""Text chunking service for splitting documents into manageable pieces."""

import re
from dataclasses import dataclass
from typing import Any

import tiktoken


@dataclass
class ChunkConfig:
    """Configuration for text chunking."""

    target_chunk_size: int = 600  # Target number of tokens per chunk
    max_chunk_size: int = 800  # Maximum tokens per chunk
    overlap: int = 100  # Tokens to overlap between chunks
    encoding_name: str = "cl100k_base"  # OpenAI's tokenizer model


@dataclass
class TextChunk:
    """Represents a chunk of text with metadata."""

    content: str
    chunk_index: int
    start_char: int
    end_char: int
    token_count: int
    section_title: str | None = None
    page_numbers: list[int] | None = None
    metadata: dict[str, Any] | None = None


class ChunkingService:
    """Service for chunking text with configurable parameters."""

    def __init__(self, config: ChunkConfig | None = None):
        """
        Initialize chunking service.

        Args:
            config: Chunking configuration, uses defaults if None
        """
        self.config = config or ChunkConfig()
        self.encoder = tiktoken.get_encoding(self.config.encoding_name)

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text.

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens
        """
        return len(self.encoder.encode(text))

    def split_into_paragraphs(self, text: str) -> list[str]:
        """
        Split text into paragraphs.

        Args:
            text: Text to split

        Returns:
            List of paragraphs
        """
        # Split on double newlines or multiple whitespace
        paragraphs = re.split(r"\n\s*\n", text)
        return [p.strip() for p in paragraphs if p.strip()]

    def detect_section_header(self, text: str) -> str | None:
        """
        Detect if text is a section header.

        Args:
            text: Text to check

        Returns:
            Section title if detected, None otherwise
        """
        # Common section header patterns
        patterns = [
            r"^#{1,6}\s+(.+)$",  # Markdown headers
            r"^(\d+\.)+\s+(.+)$",  # Numbered sections like "1.2.3 Title"
            r"^[A-Z][A-Z\s]+$",  # ALL CAPS headers
            r"^(Introduction|Conclusion|Summary|Abstract|References):?$",
        ]

        for pattern in patterns:
            match = re.match(pattern, text.strip(), re.IGNORECASE)
            if match:
                return text.strip()

        # Check if text is short and ends without punctuation
        if len(text.strip()) < 100 and not text.strip().endswith((".", "!", "?")):
            return text.strip()

        return None

    def chunk_text(
        self,
        text: str,
        section_title: str | None = None,
        page_numbers: list[int] | None = None,
    ) -> list[TextChunk]:
        """
        Chunk text into overlapping segments.

        Args:
            text: Text to chunk
            section_title: Optional section title for metadata
            page_numbers: Optional list of page numbers for this text

        Returns:
            List of text chunks with metadata
        """
        chunks: list[TextChunk] = []
        paragraphs = self.split_into_paragraphs(text)

        if not paragraphs:
            return chunks

        current_chunk = ""
        current_start_char = 0
        chunk_index = 0
        current_section = section_title

        for para in paragraphs:
            # Check if paragraph is a section header
            header = self.detect_section_header(para)
            if header and len(para) < 200:  # Headers are usually short
                current_section = header
                # Add header to current chunk if it fits
                test_chunk = (
                    current_chunk + "\n\n" + para if current_chunk else para
                )
                if self.count_tokens(test_chunk) <= self.config.max_chunk_size:
                    current_chunk = test_chunk
                    continue

            # Try adding paragraph to current chunk
            test_chunk = (
                current_chunk + "\n\n" + para if current_chunk else para
            )
            test_tokens = self.count_tokens(test_chunk)

            if test_tokens <= self.config.target_chunk_size:
                # Paragraph fits, add it
                current_chunk = test_chunk
            elif test_tokens <= self.config.max_chunk_size:
                # Chunk is getting large but within max, finalize it
                current_chunk = test_chunk
                chunks.append(
                    self._create_chunk(
                        current_chunk,
                        chunk_index,
                        current_start_char,
                        current_section,
                        page_numbers,
                    )
                )
                chunk_index += 1

                # Start new chunk with overlap
                overlap_text = self._get_overlap_text(current_chunk)
                current_chunk = overlap_text
                current_start_char += len(current_chunk) - len(overlap_text)
            else:
                # Current chunk would exceed max size
                if current_chunk:
                    # Finalize current chunk without this paragraph
                    chunks.append(
                        self._create_chunk(
                            current_chunk,
                            chunk_index,
                            current_start_char,
                            current_section,
                            page_numbers,
                        )
                    )
                    chunk_index += 1

                    # Start new chunk with overlap
                    overlap_text = self._get_overlap_text(current_chunk)
                    current_start_char += len(current_chunk) - len(overlap_text)
                    current_chunk = overlap_text + "\n\n" + para
                else:
                    # First paragraph is too large, split it
                    current_chunk = para

                # If paragraph alone exceeds max, we need to split it further
                if self.count_tokens(current_chunk) > self.config.max_chunk_size:
                    sentence_chunks = self._split_by_sentences(para)
                    for sent_chunk in sentence_chunks:
                        chunks.append(
                            self._create_chunk(
                                sent_chunk,
                                chunk_index,
                                current_start_char,
                                current_section,
                                page_numbers,
                            )
                        )
                        chunk_index += 1
                        current_start_char += len(sent_chunk)
                    current_chunk = ""

        # Add final chunk if any content remains
        if current_chunk.strip():
            chunks.append(
                self._create_chunk(
                    current_chunk,
                    chunk_index,
                    current_start_char,
                    current_section,
                    page_numbers,
                )
            )

        return chunks

    def _get_overlap_text(self, text: str) -> str:
        """
        Get overlap text from end of current chunk.

        Args:
            text: Text to get overlap from

        Returns:
            Overlap text
        """
        tokens = self.encoder.encode(text)
        if len(tokens) <= self.config.overlap:
            return text

        overlap_tokens = tokens[-self.config.overlap :]
        return self.encoder.decode(overlap_tokens)

    def _split_by_sentences(self, text: str) -> list[str]:
        """
        Split text by sentences when paragraph is too large.

        Args:
            text: Text to split

        Returns:
            List of sentence groups that fit within max size
        """
        # Simple sentence splitting
        sentences = re.split(r"(?<=[.!?])\s+", text)
        chunks = []
        current = ""

        for sentence in sentences:
            test = current + " " + sentence if current else sentence
            if self.count_tokens(test) <= self.config.max_chunk_size:
                current = test
            else:
                if current:
                    chunks.append(current)
                current = sentence

        if current:
            chunks.append(current)

        return chunks

    def _create_chunk(
        self,
        content: str,
        chunk_index: int,
        start_char: int,
        section_title: str | None,
        page_numbers: list[int] | None,
    ) -> TextChunk:
        """
        Create a TextChunk object.

        Args:
            content: Chunk content
            chunk_index: Index of chunk
            start_char: Starting character position
            section_title: Optional section title
            page_numbers: Optional page numbers

        Returns:
            TextChunk object
        """
        return TextChunk(
            content=content.strip(),
            chunk_index=chunk_index,
            start_char=start_char,
            end_char=start_char + len(content),
            token_count=self.count_tokens(content),
            section_title=section_title,
            page_numbers=page_numbers,
            metadata={
                "has_section_title": section_title is not None,
                "has_page_numbers": page_numbers is not None and len(page_numbers) > 0,
            },
        )
