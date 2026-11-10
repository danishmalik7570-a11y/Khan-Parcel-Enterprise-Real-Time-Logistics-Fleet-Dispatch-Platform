# =============================================================================
# Khan Parcel — Makefile
# =============================================================================
# Usage: make <target>
# =============================================================================

.DEFAULT_GOAL := help
.PHONY: help up down build restart logs web-logs asgi-logs worker-logs \
        migrate makemigrations seed shell dbshell \
        test test-fast test-cov lint typecheck format quality \
        worker beat simulate loadtest \
        clean purge

# ─── Colors ──────────────────────────────────────────────────────────────────
GREEN  := \033[0;32m
YELLOW := \033[0;33m
CYAN   := \033[0;36m
RESET  := \033[0m

# ─── Docker ──────────────────────────────────────────────────────────────────
COMPOSE := docker compose
EXEC    := $(COMPOSE) exec web
MANAGE  := $(EXEC) python manage.py

help: ## Show this help
	@echo ""
	@echo "$(CYAN)Khan Parcel$(RESET) — Available commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(RESET) %s\n", $$1, $$2}'
	@echo ""

# ─── Docker Compose ─────────────────────────────────────────────────────────
up: ## Start all services
	$(COMPOSE) up -d
	@echo "$(GREEN)✔ All services started$(RESET)"
	@echo "  Web:     http://localhost:8000"
	@echo "  ASGI:    http://localhost:8001"
	@echo "  API Docs: http://localhost:8000/api/docs/"
	@echo "  MinIO:   http://localhost:9001"
	@echo "  MailHog: http://localhost:8025"
	@echo "  Portal:  http://localhost:5173 (if running)"

down: ## Stop all services
	$(COMPOSE) down

build: ## Build/rebuild all images
	$(COMPOSE) build

rebuild: ## Force rebuild without cache
	$(COMPOSE) build --no-cache

restart: ## Restart all services
	$(COMPOSE) restart

logs: ## Follow all logs
	$(COMPOSE) logs -f

web-logs: ## Follow web server logs
	$(COMPOSE) logs -f web

asgi-logs: ## Follow ASGI server logs
	$(COMPOSE) logs -f asgi

worker-logs: ## Follow Celery worker logs
	$(COMPOSE) logs -f worker

# ─── Django Management ──────────────────────────────────────────────────────
migrate: ## Run database migrations
	$(MANAGE) migrate --noinput
	@echo "$(GREEN)✔ Migrations applied$(RESET)"

makemigrations: ## Create new migrations
	$(MANAGE) makemigrations

seed: ## Seed database with demo data
	$(MANAGE) seed_demo_data
	@echo "$(GREEN)✔ Demo data seeded$(RESET)"

shell: ## Django shell (shell_plus if available)
	$(MANAGE) shell_plus 2>/dev/null || $(MANAGE) shell

dbshell: ## Database shell (psql)
	$(COMPOSE) exec postgres psql -U khanparcel -d khanparcel

superuser: ## Create a superuser
	$(MANAGE) createsuperuser

collectstatic: ## Collect static files
	$(MANAGE) collectstatic --noinput

# ─── Testing ────────────────────────────────────────────────────────────────
test: ## Run all tests with coverage
	$(EXEC) pytest --tb=short -ra

test-fast: ## Run tests in parallel (no coverage)
	$(EXEC) pytest -x --no-cov -n auto

test-cov: ## Run tests with HTML coverage report
	$(EXEC) pytest --cov-report=html
	@echo "$(GREEN)✔ Coverage report: htmlcov/index.html$(RESET)"

test-unit: ## Run unit tests only
	$(EXEC) pytest tests/unit/ -x --no-cov

test-integration: ## Run integration tests only
	$(EXEC) pytest tests/integration/ --no-cov

test-e2e: ## Run end-to-end tests
	$(EXEC) pytest tests/e2e/ --no-cov -m e2e

# ─── Code Quality ───────────────────────────────────────────────────────────
lint: ## Run ruff linter
	$(EXEC) ruff check apps/ config/ tests/

lint-fix: ## Run ruff linter with auto-fix
	$(EXEC) ruff check apps/ config/ tests/ --fix

format: ## Format code with black + ruff
	$(EXEC) black apps/ config/ tests/
	$(EXEC) ruff check apps/ config/ tests/ --fix --select I

typecheck: ## Run mypy type checking
	$(EXEC) mypy apps/ config/

quality: lint typecheck ## Run all quality checks

audit: ## Security audit dependencies
	$(EXEC) pip-audit
	$(EXEC) bandit -r apps/ -c pyproject.toml

# ─── Celery ─────────────────────────────────────────────────────────────────
worker: ## Start Celery worker (foreground, for dev)
	$(EXEC) celery -A config.celery worker --loglevel=info -Q default,dispatch,notifications,payments,reports

beat: ## Start Celery beat (foreground, for dev)
	$(EXEC) celery -A config.celery beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler

flower: ## Start Flower (Celery monitoring)
	$(EXEC) celery -A config.celery flower --port=5555

# ─── Simulation & Load Testing ─────────────────────────────────────────────
simulate: ## Run day simulation script
	$(EXEC) python scripts/simulate_day.py

loadtest: ## Run Locust load tests
	$(EXEC) locust -f tests/load/locustfile.py --headless \
		-u 100 -r 10 --run-time 5m \
		--host http://localhost:8000

# ─── Portal ─────────────────────────────────────────────────────────────────
portal-install: ## Install portal dependencies
	cd portal && npm install

portal-dev: ## Start portal dev server
	cd portal && npm run dev

portal-build: ## Build portal for production
	cd portal && npm run build

# ─── Cleanup ────────────────────────────────────────────────────────────────
clean: ## Remove compiled Python files and caches
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ .coverage
	@echo "$(GREEN)✔ Cleaned$(RESET)"

purge: down ## Stop services and remove all data volumes
	$(COMPOSE) down -v --remove-orphans
	@echo "$(YELLOW)⚠ All data volumes removed$(RESET)"
