.PHONY: tests all-containers all-docker web frontend db logs logs-web logs-frontend logs-db backup help import-fdc import-custom-drvs food-editor test-frontend

tests:
	PYTHONPATH=src pytest $(ARGS)
	@echo "Running frontend unit tests..."
	$(MAKE) test-frontend

test-frontend: ## Run frontend unit tests inside the Docker container.
	@echo "Building frontend-test service (if necessary)..."
	docker-compose build frontend-test
	@echo "Executing frontend tests (npm run test:unit) using frontend-test service..."
	docker-compose run --rm frontend-test npm run test:unit

# Docker workflow commands
# Usage:
# make container [SERVICE=service_name]  # Rebuilds, stops, and starts (detached). No SERVICE means all.
# make docker [SERVICE=service_name]    # Builds and starts with logs (attached). No SERVICE means all.

SERVICE ?= "" # Default to empty (all services). Override with e.g., SERVICE=web

container:
ifeq ($(SERVICE),"")
	@echo "Building all Docker images..."
	docker-compose build
	@echo "Stopping and removing all existing containers..."
	docker-compose down
	@echo "Starting all new containers in detached mode..."
	docker-compose up -d
	@echo "All containers started."
else
	@echo "Building Docker image for service: $(SERVICE)..."
	docker-compose build $(SERVICE)
	@echo "Restarting service: $(SERVICE) in detached mode with new build..."
	# --no-deps ensures only the specified service is started/restarted.
	# --force-recreate ensures the container is replaced.
	# --build ensures the image for the service is built before starting.
	docker-compose up -d --force-recreate --no-deps --build $(SERVICE)
	@echo "Service $(SERVICE) (re)started."
endif
	@echo "Container operation complete. Use 'docker-compose ps' to see running containers."

docker:
ifeq ($(SERVICE),"")
	@echo "Building all Docker images..."
	docker-compose build
	@echo "Starting all containers and attaching to logs... Press Ctrl+C to stop."
	docker-compose up
else
	@echo "Building Docker image for service: $(SERVICE)..."
	docker-compose build $(SERVICE)
	@echo "Starting service $(SERVICE) and its dependencies, attaching to logs... Press Ctrl+C to stop."
	# 'docker-compose up $(SERVICE)' will also start dependencies of $(SERVICE).
	docker-compose up $(SERVICE)
endif
	@echo "Containers stopped."

# --- Generic Docker Operations ---
all-containers: ## Build all images, then stop, remove, and restart all containers detached.
	@echo "Building all Docker images..."
	docker-compose build
	@echo "Stopping and removing all existing containers..."
	docker-compose down
	@echo "Starting all new containers in detached mode..."
	docker-compose up -d
	@echo "All containers started. Use 'make logs' or 'docker-compose ps' to see status."

all-docker: ## Build all images, then start all containers and attach to logs. Ctrl+C to stop.
	@echo "Building all Docker images..."
	docker-compose build
	@echo "Starting all containers and attaching to logs... Press Ctrl+C to stop."
	docker-compose up
	@echo "Containers stopped."

# --- Service-Specific Operations ---
# Rebuild and restart a specific service in detached mode.

web: ## Rebuild and restart the 'web' service.
	@echo "Building Docker image for service: web..."
	docker-compose build web
	@echo "Restarting service: web in detached mode with new build..."
	docker-compose up -d --force-recreate --no-deps --build web
	@echo "Service web (re)started. Use 'make logs-web' to view its logs."

frontend: ## Rebuild and restart the 'frontend' service.
	@echo "Building Docker image for service: frontend..."
	docker-compose build frontend
	@echo "Restarting service: frontend in detached mode with new build..."
	docker-compose up -d --force-recreate --no-deps --build frontend
	@echo "Service frontend (re)started. Use 'make logs-frontend' to view its logs."

db: ## Rebuild (if applicable) and restart the 'db' service.
	@echo "Building Docker image for service: db (if build steps defined)..."
	docker-compose build db
	@echo "Restarting service: db in detached mode with new build..."
	docker-compose up -d --force-recreate --no-deps --build db
	@echo "Service db (re)started. Use 'make logs-db' to view its logs."

# --- Logging Operations ---

logs: ## Tail logs for all services.
	@echo "Tailing logs for all services... Press Ctrl+C to stop."
	docker-compose logs -f

logs-web: ## Tail logs for the 'web' service.
	@echo "Tailing logs for service: web... Press Ctrl+C to stop."
	docker-compose logs -f web

logs-frontend: ## Tail logs for the 'frontend' service.
	@echo "Tailing logs for service: frontend... Press Ctrl+C to stop."
	docker-compose logs -f frontend

logs-db: ## Tail logs for the 'db' service.
	@echo "Tailing logs for service: db... Press Ctrl+C to stop."
	docker-compose logs -f db

# --- Database Backup ---

backup: ## Create a timestamped backup of the PostgreSQL database in your home directory.
	@echo "Ensuring 'db' service is running for backup..."
	@docker-compose up -d db # Ensure the db service is running, start if not (detached)
	@echo "Creating database backup..."
	$(eval BACKUP_FILE := $(HOME)/mealprep_db_backup_$(shell date +%Y%m%d-%H%M%S).dump)
	@echo "Backup will be saved to: $(BACKUP_FILE)"
	@docker-compose exec -T db sh -c 'pg_dump -U "$$POSTGRES_USER" -d "$$POSTGRES_DB" -Fc' > "$(BACKUP_FILE)" && \
		echo "Database backup completed successfully: $(BACKUP_FILE)" || \
		(echo "ERROR: Database backup failed." && rm -f "$(BACKUP_FILE)" && exit 1)

# --- Utility ---

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Django Management Commands
# Example usage: make import-fdc ARGS="--delete-before-import"
import-fdc:
	@echo "Ensuring web service is running..."
	docker-compose up -d web
	@echo "Importing FDC foundational data..."
	docker-compose exec web python manage.py import_fdc_foundational $(ARGS)

import-custom-drvs:
	@echo "Ensuring web service is running..."
	docker-compose up -d web
	@echo "Importing custom DRVs..."
	docker-compose exec web python manage.py import_custom_drvs $(ARGS)

# Food Editor target: runs the FastAPI server for the food editor
food-editor:
	@echo "Starting Food Editor API using uvicorn..."
	echo "Activating virtual environment..."; 
	PYTHONPATH=food_editor_ui/backend . .venv/bin/activate && uvicorn app:app --reload --port 8008

migrate: ## Create Django migrations in the web container
	@echo "Making Django migrations..."
	docker-compose exec web python manage.py migrate
