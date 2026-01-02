.PHONY: up down logs psql reset health help

# Load environment variables from .env if it exists
-include .env
export

help:
	@echo "Available targets:"
	@echo "  up      - Start infrastructure (Postgres and Kafka)"
	@echo "  down    - Stop infrastructure"
	@echo "  logs    - Tail logs from all containers"
	@echo "  psql    - Connect to Postgres database"
	@echo "  reset   - Destroy volumes and restart infrastructure"
	@echo "  health  - Check container health status"

up:
	@echo "Starting infrastructure..."
	docker-compose up -d
	@echo "Waiting for services to be healthy..."
	@sleep 5
	@$(MAKE) health

down:
	@echo "Stopping infrastructure..."
	docker-compose down

logs:
	docker-compose logs -f

psql:
	@echo "Connecting to Postgres..."
	@docker exec -it fleetops-postgres psql -U ${POSTGRES_USER:-postgres} -d ${POSTGRES_DB:-fleetops}

reset:
	@echo "Destroying volumes and restarting infrastructure..."
	docker-compose down -v
	docker-compose up -d
	@echo "Waiting for services to be healthy..."
	@sleep 5
	@$(MAKE) health

health:
	@echo "Checking container health..."
	@echo "Postgres:"
	@docker inspect --format='{{.State.Health.Status}}' fleetops-postgres 2>/dev/null || echo "  Container not running"
	@echo "Kafka:"
	@docker inspect --format='{{.State.Health.Status}}' fleetops-kafka 2>/dev/null || echo "  Container not running"
	@echo ""
	@echo "Container status:"
	@docker-compose ps