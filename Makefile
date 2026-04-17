.PHONY: help setup dev test lint clean seed

help: ## Show help
	@grep -E '^[a-zA-Z_-]+:.*?## .*
$$
' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n",
$$
1, 
$$
2}'

setup: ## First-time setup
	@echo "🔧 Setting up Grant Path AI..."
	python -m pip install -r requirements.txt
	python -m pip install -e ".[dev]"
	@test -f .env || cp .env.example .env
	@echo "📦 Installing frontend..."
	cd packages/web && npm install
	@echo "✅ Done! Add GEMINI_API_KEY to .env, then: make dev"

dev: ## Start all services
	@make -j3 dev-api dev-models dev-web

dev-api: ## API server only
	uvicorn packages.api.main:create_app --factory --reload --host 0.0.0.0 --port 8000

dev-models: ## Local model server
	uvicorn packages.ai.local_models_server:app --host 0.0.0.0 --port 8001

dev-web: ## Frontend
	cd packages/web && npm run dev

dev-docker: ## Docker full stack
	docker compose -f docker/docker-compose.yml up --build

db-setup: ## Create database tables
	python -m packages.database.migrations.runner

seed: ## Load sample data
	python -m packages.database.seed.seed

db-reset: ## Reset database
	python -m packages.database.migrations.runner --reset
	make seed

test: ## Run all tests
	pytest packages/ -v --tb=short

test-engine: ## Tier 0 tests (no API keys needed)
	pytest packages/engine/tests/ -v

test-api: ## API tests
	pytest packages/api/tests/ -v

test-cov: ## Tests with coverage
	pytest packages/ --cov=packages --cov-report=html --cov-report=term

lint: ## Lint code
	ruff check packages/
	ruff format packages/ --check

format: ## Auto-format
	ruff format packages/

clean: ## Cleanup
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov .coverage
