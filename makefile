# Makefile

# Name of the web service in docker compose
SERVICE_NAME := web

# Lint command
lint:
	docker compose exec $(SERVICE_NAME) ruff format
	docker compose exec $(SERVICE_NAME) djhtml templates
	docker compose exec $(SERVICE_NAME) pylint core apps tests

# Test command with coverage
test:
	docker compose exec $(SERVICE_NAME) pytest -n auto --cov=apps --cov-report=html:.app_coverage --cov-report=term $(ARGS)

# Shell command
shell:
	docker compose exec $(SERVICE_NAME) python manage.py shell_plus

# makemigrations command
makemigrations:
	docker compose exec $(SERVICE_NAME) python manage.py makemigrations
	make migrate

# migrate command
migrate:
	docker compose exec $(SERVICE_NAME) python manage.py migrate

# Restore the database from a backup
restore:
	docker compose exec $(SERVICE_NAME) python manage.py restore_db --no-input

# Restore the database from production
restore-prod:
	docker compose exec $(SERVICE_NAME) python manage.py restore_db -s production --no-input

# Restore from development
restore-dev:
	docker compose exec $(SERVICE_NAME) python manage.py restore_db -s develop --no-input

# Create superuser
superuser:
	docker compose exec $(SERVICE_NAME) python manage.py createsuperuser

# Build the frontend
build-frontend:
	docker compose exec frontend npm run build

stop:
	make build-frontend
	docker compose down
	
restart:
	docker compose restart