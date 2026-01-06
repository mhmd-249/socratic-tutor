.PHONY: help dev backend frontend migrate test clean install setup

help:
	@echo "Socratic Tutor - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make setup      - Initial project setup (install dependencies)"
	@echo "  make install    - Install all dependencies"
	@echo ""
	@echo "Development:"
	@echo "  make dev        - Start all services (PostgreSQL, backend, frontend)"
	@echo "  make backend    - Start backend only"
	@echo "  make frontend   - Start frontend only"
	@echo ""
	@echo "Database:"
	@echo "  make migrate    - Run database migrations"
	@echo "  make db-up      - Start PostgreSQL only"
	@echo "  make db-down    - Stop PostgreSQL"
	@echo ""
	@echo "Testing:"
	@echo "  make test       - Run all tests"
	@echo "  make test-backend   - Run backend tests only"
	@echo "  make test-frontend  - Run frontend tests only"
	@echo ""
	@echo "Code Quality:"
	@echo "  make format     - Format code (Black + Prettier)"
	@echo "  make lint       - Lint code (Ruff + ESLint)"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean      - Clean up generated files and caches"
	@echo "  make clean-all  - Clean everything including docker volumes"

setup: install
	@echo "Setting up environment files..."
	@if [ ! -f backend/.env ]; then cp backend/.env.example backend/.env; fi
	@if [ ! -f frontend/.env.local ]; then cp frontend/.env.local.example frontend/.env.local; fi
	@echo "Setup complete! Please update .env files with your credentials."

install:
	@echo "Installing backend dependencies..."
	cd backend && poetry install
	@echo "Installing frontend dependencies..."
	cd frontend && npm install
	@echo "Dependencies installed successfully!"

dev:
	@echo "Starting all services with docker-compose..."
	docker-compose up

backend:
	@echo "Starting backend only..."
	cd backend && poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend:
	@echo "Starting frontend only..."
	cd frontend && npm run dev

db-up:
	@echo "Starting PostgreSQL..."
	docker-compose up postgres -d

db-down:
	@echo "Stopping PostgreSQL..."
	docker-compose down postgres

migrate:
	@echo "Running database migrations..."
	cd backend && poetry run alembic upgrade head

test:
	@echo "Running all tests..."
	@make test-backend
	@make test-frontend

test-backend:
	@echo "Running backend tests..."
	cd backend && poetry run pytest

test-frontend:
	@echo "Running frontend tests..."
	cd frontend && npm test

format:
	@echo "Formatting backend code with Black..."
	cd backend && poetry run black .
	@echo "Formatting frontend code with Prettier..."
	cd frontend && npx prettier --write .

lint:
	@echo "Linting backend code with Ruff..."
	cd backend && poetry run ruff check .
	@echo "Linting frontend code with ESLint..."
	cd frontend && npm run lint

clean:
	@echo "Cleaning up generated files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "node_modules" -prune -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".next" -exec rm -rf {} + 2>/dev/null || true
	cd backend && rm -rf dist/ build/ *.egg-info
	@echo "Cleanup complete!"

clean-all: clean
	@echo "Stopping and removing all Docker containers and volumes..."
	docker-compose down -v
	@echo "Complete cleanup done!"
