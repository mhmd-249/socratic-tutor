# Book Ingestion Scripts

## Overview

The book ingestion pipeline extracts text from PDF files, detects chapters, chunks the content, generates embeddings, and stores everything in the database.

## Setup

1. **Install dependencies** (if not already done):
   ```bash
   cd backend
   poetry install
   ```

2. **Configure environment variables** in `backend/.env`:
   ```bash
   OPENAI_API_KEY=your-openai-api-key-here
   DATABASE_URL=postgresql://postgres:postgres@localhost:5432/socratic_tutor
   ```

3. **Ensure PostgreSQL is running**:
   ```bash
   cd ..  # Back to project root
   docker-compose up postgres -d
   ```

## Usage

### Basic Usage

Ingest a PDF book with minimal options:

```bash
cd backend
python -m scripts.ingest_book \
  --pdf path/to/your/book.pdf \
  --title "Introduction to Machine Learning" \
  --author "John Doe"
```

### Advanced Usage

Customize chunking parameters:

```bash
python -m scripts.ingest_book \
  --pdf path/to/your/book.pdf \
  --title "Deep Learning Fundamentals" \
  --author "Jane Smith" \
  --description "A comprehensive guide to deep learning concepts" \
  --target-chunk-size 500 \
  --max-chunk-size 700 \
  --overlap 80
```

### Force Re-ingestion

Automatically delete existing book and re-ingest (useful for scripts/CI):

```bash
python -m scripts.ingest_book \
  --pdf path/to/your/book.pdf \
  --title "Introduction to Machine Learning" \
  --author "John Doe" \
  --force
```

## Command-Line Options

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--pdf` | Yes | - | Path to the PDF file to ingest |
| `--title` | Yes | - | Title of the book |
| `--author` | Yes | - | Author of the book |
| `--description` | No | "" | Book description |
| `--target-chunk-size` | No | 600 | Target size for text chunks (in tokens) |
| `--max-chunk-size` | No | 800 | Maximum size for text chunks (in tokens) |
| `--overlap` | No | 100 | Number of tokens to overlap between chunks |
| `--force` | No | False | Automatically delete existing book and re-ingest (non-interactive) |

## How It Works

### 0. Idempotency Check

Before ingestion, the script checks if a book with the same title already exists:

**Interactive Mode (default):**
- Prompts user with three options:
  - **[s] Skip**: Abort ingestion, no changes made
  - **[d] Delete**: Delete existing book and all related data (chapters, chunks), then re-ingest
  - **[c] Create duplicate**: Proceed with ingestion, creating a duplicate entry

**Force Mode (`--force` flag):**
- Automatically deletes existing book and re-ingests
- No user prompt (useful for automation/CI)
- Logs warning that book is being replaced

### 1. PDF Text Extraction

Uses PyMuPDF (fitz) to extract text from the PDF document.

### 2. Chapter Detection

Automatically detects chapters using patterns like:
- `Chapter 1: Title`
- `Chapter 1`
- `1. Title`
- `CHAPTER 1: Title`

If no chapters are detected, treats the entire book as a single chapter.

### 3. Text Chunking

Splits chapter text into manageable chunks:
- **Paragraph-based**: Preserves natural text boundaries
- **Token-aware**: Respects token limits for embeddings
- **Overlapping**: Maintains context between chunks
- **Section headers**: Detected and preserved in metadata

### 4. Embedding Generation

- Uses OpenAI's `text-embedding-3-small` model (1536 dimensions)
- Batches requests for efficiency (100 texts per batch)
- Implements exponential backoff for rate limiting
- Handles errors with retry logic

### 5. Database Storage

Stores all data in PostgreSQL:
- **Books**: Title, author, description
- **Chapters**: Number, title, summary
- **Chunks**: Content, embeddings, metadata with pgvector indexing

## Pipeline Output

The script provides detailed logging:

```
2026-01-06 - INFO - Starting book ingestion: Introduction to ML
2026-01-06 - INFO - Step 1: Extracting text from PDF...
2026-01-06 - INFO - Extracted 150000 characters
2026-01-06 - INFO - Step 2: Detecting chapters...
2026-01-06 - INFO - Detected 10 chapters
2026-01-06 - INFO - Step 3: Creating book record...
2026-01-06 - INFO - Created book: abc123...

Processing chapter 1/10: Introduction
  Created chapter record: def456...
  Chunking text...
  Created 15 chunks
  Generating embeddings...
  Processing batch 1/1 (15 texts)
  Successfully generated 15 embeddings
  Storing chunks in database...
  ✓ Stored 15 chunks
...
✓ Book ingestion complete: Introduction to ML
  - Chapters: 10
```

## Troubleshooting

### Common Issues

**1. PyMuPDF not installed:**
```bash
poetry add pymupdf
```

**2. OpenAI API key missing:**
- Check your `.env` file has `OPENAI_API_KEY` set
- Verify the key is valid

**3. Rate limiting errors:**
- The script automatically retries with exponential backoff
- If persistent, reduce batch size or add delays

**4. Chapter detection fails:**
- The script will treat the book as one chapter
- Manually specify chapter markers in the PDF if needed

**5. Database connection errors:**
- Ensure PostgreSQL is running: `docker-compose up postgres -d`
- Check `DATABASE_URL` in `.env` is correct

## Performance Notes

- **Large PDFs**: May take several minutes depending on size
- **API costs**: OpenAI embeddings cost ~$0.02 per 1M tokens
- **Rate limits**: Script handles OpenAI's rate limits automatically
- **Memory usage**: Processes chapters sequentially to manage memory

## Next Steps

After ingesting books:
1. Verify data: Query the database to confirm books/chapters/chunks
2. Test retrieval: Use the chunk repository's similarity search
3. Build chat interface: Use the embedded chunks for RAG

## Examples

### Verify Ingestion

```bash
# Connect to database
docker-compose exec postgres psql -U postgres -d socratic_tutor

# Check books
SELECT id, title, author FROM books;

# Check chapters for a book
SELECT id, title, chapter_number FROM chapters WHERE book_id = 'your-book-id';

# Check chunk count
SELECT chapter_id, COUNT(*) FROM chunks GROUP BY chapter_id;
```

### Test Similarity Search

```python
from app.repositories.chunk import ChunkRepository
from app.services.embedding_service import EmbeddingService

# Generate query embedding
embedding_service = EmbeddingService()
query = "What is supervised learning?"
query_embedding = await embedding_service.generate_embedding(query)

# Search for similar chunks
chunk_repo = ChunkRepository(session)
results = await chunk_repo.search_by_embedding(
    embedding=query_embedding,
    limit=5
)
```
