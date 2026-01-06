"""
Book ingestion script for processing PDFs into the database.

Usage:
    python -m scripts.ingest_book --pdf path/to/book.pdf --title "Book Title" --author "Author"
"""

import argparse
import asyncio
import logging
import re
import sys
import uuid
from datetime import datetime
from pathlib import Path

import fitz  # PyMuPDF

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.repositories.book import BookRepository
from app.repositories.chapter import ChapterRepository
from app.repositories.chunk import ChunkRepository
from app.services.chunking_service import ChunkConfig, ChunkingService
from app.services.embedding_service import EmbeddingService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class PDFProcessor:
    """Handles PDF text extraction and chapter detection."""

    def __init__(self, pdf_path: str):
        """
        Initialize PDF processor.

        Args:
            pdf_path: Path to PDF file
        """
        self.pdf_path = pdf_path
        self.doc = None

    def __enter__(self):
        """Open PDF document."""
        self.doc = fitz.open(self.pdf_path)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close PDF document."""
        if self.doc:
            self.doc.close()

    def extract_text(self) -> str:
        """
        Extract all text from PDF.

        Returns:
            Full text content
        """
        text_parts = []
        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            text_parts.append(page.get_text())

        return "\n\n".join(text_parts)

    def extract_with_pages(self) -> list[tuple[int, str]]:
        """
        Extract text with page numbers.

        Returns:
            List of (page_number, text) tuples
        """
        pages = []
        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            text = page.get_text()
            pages.append((page_num + 1, text))

        return pages

    @staticmethod
    def detect_chapters(text: str) -> list[dict]:
        """
        Detect chapter boundaries in text.

        Args:
            text: Full text content

        Returns:
            List of chapter dictionaries with title and content
        """
        # Patterns for detecting chapters
        patterns = [
            r"^Chapter\s+(\d+):?\s*(.+?)$",  # Chapter 1: Title
            r"^Chapter\s+(\d+)\s*$",  # Chapter 1
            r"^(\d+)\.\s+(.+?)$",  # 1. Title
            r"^CHAPTER\s+(\d+):?\s*(.+?)$",  # CHAPTER 1: Title
        ]

        chapters = []
        lines = text.split("\n")
        current_chapter = None
        current_content = []

        for i, line in enumerate(lines):
            line = line.strip()

            # Try to match chapter patterns
            is_chapter = False
            for pattern in patterns:
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    # Save previous chapter if exists
                    if current_chapter:
                        current_chapter["content"] = "\n".join(
                            current_content
                        ).strip()
                        chapters.append(current_chapter)

                    # Start new chapter
                    chapter_num = int(match.group(1))
                    chapter_title = (
                        match.group(2).strip() if match.lastindex > 1 else f"Chapter {chapter_num}"
                    )

                    current_chapter = {
                        "chapter_number": chapter_num,
                        "title": chapter_title,
                    }
                    current_content = []
                    is_chapter = True
                    break

            if not is_chapter and current_chapter:
                current_content.append(line)

        # Add final chapter
        if current_chapter:
            current_chapter["content"] = "\n".join(current_content).strip()
            chapters.append(current_chapter)

        return chapters


class BookIngestionPipeline:
    """Main pipeline for ingesting books into the database."""

    def __init__(
        self,
        pdf_path: str,
        title: str,
        author: str,
        description: str = "",
        chunk_config: ChunkConfig | None = None,
        force: bool = False,
    ):
        """
        Initialize ingestion pipeline.

        Args:
            pdf_path: Path to PDF file
            title: Book title
            author: Book author
            description: Book description
            chunk_config: Optional chunking configuration
            force: If True, automatically delete existing book and re-ingest
        """
        self.pdf_path = pdf_path
        self.title = title
        self.author = author
        self.description = description or f"Book: {title} by {author}"
        self.force = force

        self.chunking_service = ChunkingService(chunk_config)
        self.embedding_service = EmbeddingService()

    async def _check_existing_book(self) -> uuid.UUID | None:
        """
        Check if a book with the same title already exists.

        Returns:
            UUID of existing book, or None if not found
        """
        async with AsyncSessionLocal() as session:
            book_repo = BookRepository(session)
            existing_books = await book_repo.get_by_title(self.title)

            # Look for exact match (case-insensitive)
            for book in existing_books:
                if book.title.lower() == self.title.lower():
                    return book.id

            return None

    async def _delete_existing_book(self, book_id: uuid.UUID):
        """
        Delete an existing book and all related data.

        Args:
            book_id: UUID of book to delete
        """
        logger.info(f"Deleting existing book and all related data...")

        async with AsyncSessionLocal() as session:
            book_repo = BookRepository(session)

            # Delete book (cascades to chapters, chunks, etc.)
            deleted = await book_repo.delete(book_id)
            await session.commit()

            if deleted:
                logger.info("✓ Existing book deleted successfully")
            else:
                logger.warning("⚠ Book not found (may have been already deleted)")

    def _prompt_user_action(self) -> str:
        """
        Prompt user for action when book already exists.

        Returns:
            User's choice: 'skip', 'delete', or 'duplicate'
        """
        print("\n" + "=" * 60)
        print(f"⚠️  BOOK ALREADY EXISTS: '{self.title}'")
        print("=" * 60)
        print("\nWhat would you like to do?")
        print("  [s] Skip - Don't ingest this book")
        print("  [d] Delete existing and re-ingest")
        print("  [c] Create duplicate anyway")
        print()

        while True:
            choice = input("Enter your choice (s/d/c): ").lower().strip()

            if choice == 's':
                return 'skip'
            elif choice == 'd':
                return 'delete'
            elif choice == 'c':
                return 'duplicate'
            else:
                print("Invalid choice. Please enter 's', 'd', or 'c'.")

    async def run(self):
        """Run the complete ingestion pipeline."""
        logger.info(f"Starting book ingestion: {self.title}")
        logger.info(f"PDF: {self.pdf_path}")

        # Check for existing book
        existing_book_id = await self._check_existing_book()

        if existing_book_id:
            if self.force:
                # Force mode: automatically delete and re-ingest
                logger.warning(
                    f"⚠️  Book '{self.title}' already exists (ID: {existing_book_id})"
                )
                logger.info("🔄 Force mode enabled - deleting and re-ingesting")
                await self._delete_existing_book(existing_book_id)
            else:
                # Interactive mode: prompt user
                action = self._prompt_user_action()

                if action == 'skip':
                    logger.info("⏭️  Skipping ingestion (user choice)")
                    print("\n✓ Skipped - no changes made\n")
                    return

                elif action == 'delete':
                    await self._delete_existing_book(existing_book_id)
                    logger.info("♻️  Re-ingesting book after deletion")

                elif action == 'duplicate':
                    logger.warning(
                        "⚠️  Creating duplicate book (user requested)"
                    )

        # Step 1: Extract text from PDF
        logger.info("Step 1: Extracting text from PDF...")
        with PDFProcessor(self.pdf_path) as processor:
            full_text = processor.extract_text()
            logger.info(f"Extracted {len(full_text)} characters")

            # Step 2: Detect chapters
            logger.info("Step 2: Detecting chapters...")
            chapters_data = processor.detect_chapters(full_text)

            if not chapters_data:
                logger.warning(
                    "No chapters detected. Treating entire book as one chapter."
                )
                chapters_data = [
                    {
                        "chapter_number": 1,
                        "title": self.title,
                        "content": full_text,
                    }
                ]

            logger.info(f"Detected {len(chapters_data)} chapters")

        # Step 3: Create book in database
        logger.info("Step 3: Creating book record...")
        async with AsyncSessionLocal() as session:
            book_repo = BookRepository(session)
            book_id = uuid.uuid4()

            book = await book_repo.create(
                {
                    "id": book_id,
                    "title": self.title,
                    "author": self.author,
                    "description": self.description,
                    "created_at": datetime.utcnow(),
                }
            )
            await session.commit()
            logger.info(f"Created book: {book.id}")

        # Step 4: Process each chapter
        for idx, chapter_data in enumerate(chapters_data, 1):
            logger.info(
                f"\nProcessing chapter {idx}/{len(chapters_data)}: "
                f"{chapter_data['title']}"
            )

            await self._process_chapter(book_id, chapter_data)

        logger.info(f"\n✓ Book ingestion complete: {self.title}")
        logger.info(f"  - Chapters: {len(chapters_data)}")

    async def _process_chapter(self, book_id: uuid.UUID, chapter_data: dict):
        """
        Process a single chapter: chunk, embed, and store.

        Args:
            book_id: Book UUID
            chapter_data: Chapter data dictionary
        """
        # Create chapter record
        async with AsyncSessionLocal() as session:
            chapter_repo = ChapterRepository(session)
            chapter_id = uuid.uuid4()

            # Extract summary (first 500 chars of content)
            content = chapter_data["content"]
            summary = content[:500] + "..." if len(content) > 500 else content

            chapter = await chapter_repo.create(
                {
                    "id": chapter_id,
                    "book_id": book_id,
                    "title": chapter_data["title"],
                    "chapter_number": chapter_data["chapter_number"],
                    "summary": summary,
                    "prerequisites": [],
                    "key_concepts": [],
                    "created_at": datetime.utcnow(),
                }
            )
            await session.commit()
            logger.info(f"  Created chapter record: {chapter.id}")

        # Chunk the text
        logger.info("  Chunking text...")
        text_chunks = self.chunking_service.chunk_text(
            content, section_title=chapter_data["title"]
        )
        logger.info(f"  Created {len(text_chunks)} chunks")

        # Prepare chunk data
        chunk_dicts = []
        for chunk in text_chunks:
            chunk_dicts.append(
                {
                    "content": chunk.content,
                    "chunk_index": chunk.chunk_index,
                    "section_title": chunk.section_title,
                    "chunk_metadata": chunk.metadata or {},
                }
            )

        # Generate embeddings
        logger.info("  Generating embeddings...")
        chunks_with_embeddings = await self.embedding_service.embed_chunks(
            chunk_dicts
        )

        # Store chunks in database
        logger.info("  Storing chunks in database...")
        async with AsyncSessionLocal() as session:
            chunk_repo = ChunkRepository(session)

            for chunk_data in chunks_with_embeddings:
                await chunk_repo.create(
                    {
                        "id": uuid.uuid4(),
                        "chapter_id": chapter_id,
                        "content": chunk_data["content"],
                        "embedding": chunk_data["embedding"],
                        "chunk_index": chunk_data["chunk_index"],
                        "section_title": chunk_data.get("section_title"),
                        "chunk_metadata": chunk_data.get("chunk_metadata", {}),
                        "created_at": datetime.utcnow(),
                    }
                )

            await session.commit()
            logger.info(f"  ✓ Stored {len(chunks_with_embeddings)} chunks")


async def main():
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(
        description="Ingest a PDF book into the Socratic Tutor database"
    )
    parser.add_argument(
        "--pdf", required=True, help="Path to PDF file"
    )
    parser.add_argument(
        "--title", required=True, help="Book title"
    )
    parser.add_argument(
        "--author", required=True, help="Book author"
    )
    parser.add_argument(
        "--description", default="", help="Book description (optional)"
    )
    parser.add_argument(
        "--target-chunk-size",
        type=int,
        default=600,
        help="Target chunk size in tokens (default: 600)",
    )
    parser.add_argument(
        "--max-chunk-size",
        type=int,
        default=800,
        help="Maximum chunk size in tokens (default: 800)",
    )
    parser.add_argument(
        "--overlap",
        type=int,
        default=100,
        help="Overlap between chunks in tokens (default: 100)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Automatically delete existing book and re-ingest (non-interactive)",
    )

    args = parser.parse_args()

    # Validate PDF exists
    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        logger.error(f"PDF file not found: {args.pdf}")
        sys.exit(1)

    # Create chunk configuration
    chunk_config = ChunkConfig(
        target_chunk_size=args.target_chunk_size,
        max_chunk_size=args.max_chunk_size,
        overlap=args.overlap,
    )

    # Run ingestion pipeline
    pipeline = BookIngestionPipeline(
        pdf_path=str(pdf_path),
        title=args.title,
        author=args.author,
        description=args.description,
        chunk_config=chunk_config,
        force=args.force,
    )

    try:
        await pipeline.run()
    except Exception as e:
        logger.error(f"Ingestion failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
