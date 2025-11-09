# Makefile for Gradent Deployment
# Simplifies common Docker operations

.PHONY: help build up down restart logs status clean backup shell-backend shell-frontend setup

help: ## Show this help message
	@echo "Gradent Deployment Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

build: ## Build Docker images
	docker compose build

up: ## Start services in detached mode
	docker compose up -d

down: ## Stop and remove containers
	docker compose down

restart: ## Restart all services
	docker compose restart

logs: ## View logs from all services (follow mode)
	docker compose logs -f

logs-backend: ## View backend logs only
	docker compose logs -f backend

logs-frontend: ## View frontend logs only
	docker compose logs -f frontend

status: ## Show container status
	docker compose ps

clean: ## Remove containers, networks, and volumes
	docker compose down -v
	docker system prune -f

backup: ## Backup data directory
	tar -czf backup-$(shell date +%Y%m%d-%H%M%S).tar.gz data/ logs/
	@echo "Backup created: backup-$(shell date +%Y%m%d-%H%M%S).tar.gz"

shell-backend: ## Open shell in backend container
	docker compose exec backend bash

shell-frontend: ## Open shell in frontend container
	docker compose exec frontend sh

setup: ## Initialize database with mock data
	docker compose exec backend python scripts/setup_all.py

rebuild: ## Rebuild and restart services
	docker compose down
	docker compose build
	docker compose up -d

health: ## Check health of services
	@echo "Checking backend..."
	@curl -f http://localhost:8000/health && echo " ✓ Backend is healthy" || echo " ✗ Backend is not responding"
	@echo "Checking frontend..."
	@curl -f http://localhost/ > /dev/null 2>&1 && echo " ✓ Frontend is healthy" || echo " ✗ Frontend is not responding"

prod-up: ## Start services with production config
	docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

prod-down: ## Stop production services
	docker compose -f docker-compose.yml -f docker-compose.prod.yml down

update: ## Update application (git pull + rebuild)
	git pull
	docker compose build
	docker compose up -d
	@echo "Application updated successfully!"
