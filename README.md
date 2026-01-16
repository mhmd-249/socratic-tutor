# Socratic Tutor

An AI-powered Socratic teaching assistant that helps students learn AI concepts through guided dialogue.

## Tech Stack

- **Frontend**: Next.js 14, TypeScript, Tailwind CSS
- **Backend**: FastAPI, Python 3.12, SQLAlchemy
- **Database**: PostgreSQL 16 with pgvector extension
- **Authentication**: Supabase Auth
- **LLM**: Claude API (claude-sonnet-4-20250514)
- **Embeddings**: OpenAI text-embedding-3-small

## Project Structure

```
socratic-tutor/
├── frontend/          # Next.js application
├── backend/           # FastAPI application
├── docker-compose.yml # Docker services configuration
├── Makefile          # Development commands
└── CLAUDE.md         # Project context and guidelines
```

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 20+
- Poetry
- Docker & Docker Compose (optional, for containerized setup)

### Initial Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd socratic-tutor
   ```

2. Run the setup script:
   ```bash
   make setup
   ```

3. Update environment files with your credentials:
   - `backend/.env`
   - `frontend/.env.local`

### Development with Docker (Recommended)

Start all services (PostgreSQL, backend, frontend):
```bash
make dev
```

Access:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Development without Docker

1. Start PostgreSQL:
   ```bash
   make db-up
   ```

2. Run migrations:
   ```bash
   make migrate
   ```

3. Start backend (in one terminal):
   ```bash
   make backend
   ```

4. Start frontend (in another terminal):
   ```bash
   make frontend
   ```

## Available Commands

Run `make help` to see all available commands:

- `make setup` - Initial project setup
- `make dev` - Start all services
- `make backend` - Start backend only
- `make frontend` - Start frontend only
- `make migrate` - Run database migrations
- `make test` - Run all tests
- `make format` - Format code
- `make lint` - Lint code
- `make clean` - Clean up generated files

## Documentation

- See `CLAUDE.md` for detailed project context and architecture
- Backend API docs: http://localhost:8000/docs (when running)
- Frontend: `frontend/README.md`
- Backend: `backend/README.md`

## Development Guidelines

- Follow the coding standards defined in `CLAUDE.md`
- Use conventional commits (feat:, fix:, docs:, refactor:)
- Run tests and linting before committing
- Format code before committing

## License

Open
