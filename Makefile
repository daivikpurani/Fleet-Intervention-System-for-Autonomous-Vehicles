.PHONY: up down logs psql reset health help start start-reload kafka-reset kafka-check quick-start demo test test-smoke test-unit

# Load environment variables from .env if it exists
-include .env
export

help:
	@echo "Available targets:"
	@echo "  up           - Start infrastructure (Postgres and Kafka)"
	@echo "  down         - Stop infrastructure"
	@echo "  logs         - Tail logs from all containers"
	@echo "  psql         - Connect to Postgres database"
	@echo "  reset        - Destroy volumes and restart infrastructure"
	@echo "  health       - Check container health status"
	@echo "  kafka-check  - Check for Kafka cluster ID mismatch"
	@echo "  kafka-reset  - Reset Kafka and Zookeeper volumes (fixes cluster ID mismatch)"
	@echo "  start        - Start all services (infra + backend + frontend)"
	@echo "  start-reload - Start all services with auto-reload enabled"
	@echo "  quick-start  - Quick start infrastructure and database"
	@echo "  demo         - Trigger demo replay and verify system"
	@echo "  test         - Run all tests"
	@echo "  test-smoke   - Run smoke tests (requires running services)"
	@echo "  test-unit    - Run unit tests only"

up:
	@echo "Checking Docker daemon..."
	@docker info > /dev/null 2>&1 || (echo "Error: Docker daemon is not running. Please start Docker Desktop and try again." && exit 1)
	@echo "Starting infrastructure..."
	docker-compose up -d
	@echo "Waiting for services to be healthy..."
	@sleep 5
	@echo "Checking for Kafka cluster ID issues..."
	@./scripts/check_kafka_cluster_id.sh || true
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
	@KAFKA_STATUS=$$(docker inspect --format='{{.State.Health.Status}}' fleetops-kafka 2>/dev/null || echo "not_running"); \
	if [ "$$KAFKA_STATUS" = "not_running" ]; then \
		echo "  Container not running"; \
	elif [ "$$KAFKA_STATUS" != "healthy" ]; then \
		echo "  $$KAFKA_STATUS"; \
		echo "  Checking for cluster ID mismatch..."; \
		./scripts/check_kafka_cluster_id.sh 2>/dev/null || echo "  (Run 'make kafka-check' for details)"; \
	else \
		echo "  $$KAFKA_STATUS"; \
	fi
	@echo ""
	@echo "Container status:"
	@docker-compose ps

kafka-check:
	@./scripts/check_kafka_cluster_id.sh

kafka-reset:
	@./scripts/reset_kafka.sh

start:
	@./scripts/start_all.sh

start-reload:
	@./scripts/start_all.sh --reload

quick-start:
	@./scripts/quick_start.sh

demo:
	@./scripts/run_demo.sh

test:
	@echo "Running all tests..."
	@PYTHONPATH="$(PWD):$$PYTHONPATH" pytest tests/ -v -x

test-smoke:
	@echo "Running smoke tests (requires services to be running)..."
	@PYTHONPATH="$(PWD):$$PYTHONPATH" pytest tests/test_smoke.py -v

test-unit:
	@echo "Running unit tests..."
	@PYTHONPATH="$(PWD):$$PYTHONPATH" pytest tests/unit/ -v