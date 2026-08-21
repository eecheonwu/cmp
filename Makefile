# CMP Docker Development Makefile

.PHONY: help up down build logs clean init-db init-kms test shell-backend shell-frontend

help:
	@echo "CMP Docker Development Commands"
	@echo "=============================="
	@echo "up          - Start all services"
	@echo "up-prod     - Start production services"
	@echo "down        - Stop all services"
	@echo "down-v      - Stop services and remove volumes"
	@echo "build       - Build all images"
	@echo "logs        - View all logs"
	@echo "logs-backend - View backend logs"
	@echo "logs-frontend - View frontend logs"
	@echo "logs-celery  - View celery worker logs"
	@echo "init-db      - Initialize database (run migrations)"
	@echo "init-kms     - Initialize KMS key in LocalStack"
	@echo "test        - Run tests in backend container"
	@echo "shell-backend - Open shell in backend container"
	@echo "shell-frontend - Open shell in frontend container"
	@echo "clean       - Remove all containers, networks, and volumes"

up:
	docker-compose up -d

up-prod:
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

down:
	docker-compose down

down-v:
	docker-compose down -v

build:
	docker-compose build

logs:
	docker-compose logs -f

logs-backend:
	docker-compose logs -f backend

logs-frontend:
	docker-compose logs -f frontend

logs-celery:
	docker-compose logs -f celery-worker

init-db:
	docker-compose exec backend alembic upgrade head

init-kms:
	docker-compose exec localstack /tmp/localstack-setup/init-kms.sh

test:
	docker-compose exec backend pytest -v

shell-backend:
	docker-compose exec backend sh

shell-frontend:
	docker-compose exec frontend sh

clean:
	docker-compose down -v --rmi all
	docker system prune -f