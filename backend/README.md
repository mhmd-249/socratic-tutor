# Socratic Tutor Backend

FastAPI backend for the AI Socratic Tutor application.

## Setup

1. Install dependencies:
   ```bash
   poetry install
   ```

2. Copy `.env.example` to `.env` and configure:
   ```bash
   cp .env.example .env
   ```

3. Run database migrations:
   ```bash
   poetry run alembic upgrade head
   ```

4. Start the development server:
   ```bash
   poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

## Development

- Format code: `poetry run black .`
- Lint code: `poetry run ruff check .`
- Run tests: `poetry run pytest`
- Run tests with coverage: `poetry run pytest --cov`

## API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
