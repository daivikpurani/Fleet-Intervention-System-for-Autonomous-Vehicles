#!/bin/bash
# Start all services: infrastructure, backend services, and frontend
# Supports reload/watch mode for development

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
RELOAD=false
INFRA_ONLY=false
BACKEND_ONLY=false
FRONTEND_ONLY=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --reload|-r)
            RELOAD=true
            shift
            ;;
        --infra-only)
            INFRA_ONLY=true
            shift
            ;;
        --backend-only)
            BACKEND_ONLY=true
            shift
            ;;
        --frontend-only)
            FRONTEND_ONLY=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --reload, -r          Enable auto-reload for backend services (uses uvicorn --reload)"
            echo "  --infra-only          Start only infrastructure (Postgres, Kafka)"
            echo "  --backend-only        Start only backend services"
            echo "  --frontend-only       Start only frontend"
            echo "  --help, -h            Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                    Start all services without reload"
            echo "  $0 --reload           Start all services with auto-reload"
            echo "  $0 --infra-only       Start only infrastructure"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Get the project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# Function to check if a port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        return 0
    else
        return 1
    fi
}

# Function to wait for a service to be ready
wait_for_service() {
    local service_name=$1
    local port=$2
    local max_attempts=30
    local attempt=1
    
    echo -e "${BLUE}Waiting for $service_name to be ready on port $port...${NC}"
    while [ $attempt -le $max_attempts ]; do
        if check_port $port; then
            echo -e "${GREEN}$service_name is ready!${NC}"
            return 0
        fi
        sleep 1
        attempt=$((attempt + 1))
    done
    
    echo -e "${RED}$service_name failed to start on port $port${NC}"
    return 1
}

# Function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}Shutting down services...${NC}"
    
    # Kill background processes (backend services and frontend)
    jobs -p | xargs -r kill 2>/dev/null || true
    
    # NOTE: We do NOT stop infrastructure (Postgres, Kafka, Zookeeper) by default
    # This allows you to restart backend services without restarting infrastructure
    # To stop infrastructure, run: make down or docker-compose down
    
    echo -e "${GREEN}Backend services stopped${NC}"
    echo -e "${YELLOW}Infrastructure (Postgres, Kafka) is still running${NC}"
    echo -e "${YELLOW}To stop infrastructure: make down${NC}"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Start Infrastructure
if [ "$FRONTEND_ONLY" = false ]; then
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}Starting Infrastructure${NC}"
    echo -e "${BLUE}========================================${NC}"
    
    # Check if Docker is running
    if ! docker info > /dev/null 2>&1; then
        echo -e "${RED}Error: Docker daemon is not running. Please start Docker Desktop and try again.${NC}"
        exit 1
    fi
    
    # Check if infrastructure is already running
    if docker ps --format '{{.Names}}' | grep -q "^fleetops-postgres$" && \
       docker ps --format '{{.Names}}' | grep -q "^fleetops-kafka$"; then
        echo -e "${GREEN}✓ Infrastructure is already running${NC}"
        echo -e "${BLUE}  Skipping infrastructure startup...${NC}"
        # Still check health to make sure everything is working
        postgres_healthy=$(docker inspect --format='{{.State.Health.Status}}' fleetops-postgres 2>/dev/null | grep -q "healthy" && echo "true" || echo "false")
        kafka_healthy=$(docker inspect --format='{{.State.Health.Status}}' fleetops-kafka 2>/dev/null | grep -q "healthy" && echo "true" || echo "false")
        
        if [ "$postgres_healthy" = "true" ]; then
            echo -e "${GREEN}✓ Postgres is healthy${NC}"
        else
            echo -e "${YELLOW}⚠ Postgres is running but not healthy${NC}"
        fi
        
        if [ "$kafka_healthy" = "true" ]; then
            echo -e "${GREEN}✓ Kafka is healthy${NC}"
        else
            echo -e "${YELLOW}⚠ Kafka is running but not healthy${NC}"
            echo -e "${YELLOW}  Check logs: docker logs fleetops-kafka${NC}"
            echo -e "${YELLOW}  If you see 'InconsistentClusterIdException', run: make kafka-reset${NC}"
        fi
    else
        # Start infrastructure services
        echo -e "${BLUE}Starting Postgres, Zookeeper, and Kafka...${NC}"
        docker-compose up -d
    
    # Wait for services to be healthy
    echo -e "${BLUE}Waiting for infrastructure services to be healthy...${NC}"
    
    # Wait for Postgres to be healthy (max 60 seconds)
    max_wait=60
    elapsed=0
    postgres_healthy=false
    while [ $elapsed -lt $max_wait ]; do
        if docker inspect --format='{{.State.Health.Status}}' fleetops-postgres 2>/dev/null | grep -q "healthy"; then
            echo -e "${GREEN}✓ Postgres is healthy${NC}"
            postgres_healthy=true
            break
        fi
        sleep 2
        elapsed=$((elapsed + 2))
    done
    
    if [ "$postgres_healthy" = false ]; then
        echo -e "${YELLOW}⚠ Postgres did not become healthy within ${max_wait} seconds${NC}"
    fi
    
    # Wait for Kafka to be healthy (max 90 seconds - Kafka takes longer)
    max_wait=90
    elapsed=0
    kafka_healthy=false
    while [ $elapsed -lt $max_wait ]; do
        if docker inspect --format='{{.State.Health.Status}}' fleetops-kafka 2>/dev/null | grep -q "healthy"; then
            echo -e "${GREEN}✓ Kafka is healthy${NC}"
            kafka_healthy=true
            break
        fi
        if [ $((elapsed % 10)) -eq 0 ] && [ $elapsed -gt 0 ]; then
            echo -e "${YELLOW}  Waiting for Kafka... (${elapsed}s/${max_wait}s)${NC}"
        fi
        sleep 2
        elapsed=$((elapsed + 2))
    done
    
    if [ "$kafka_healthy" = false ]; then
        echo -e "${RED}⚠ Kafka did not become healthy within ${max_wait} seconds${NC}"
        echo -e "${YELLOW}  Checking for cluster ID mismatch...${NC}"
        # Check for cluster ID mismatch and attempt auto-fix
        if "$PROJECT_ROOT/scripts/check_kafka_cluster_id.sh" 2>/dev/null; then
            echo -e "${GREEN}✓ Kafka cluster ID issue detected and fixed${NC}"
            # Re-check health after fix
            sleep 5
            if docker inspect --format='{{.State.Health.Status}}' fleetops-kafka 2>/dev/null | grep -q "healthy"; then
                echo -e "${GREEN}✓ Kafka is now healthy after fix${NC}"
                kafka_healthy=true
            fi
        else
            echo -e "${YELLOW}  Services will start but may fail to connect. Check Kafka logs:${NC}"
            echo -e "${YELLOW}  docker logs fleetops-kafka${NC}"
            echo -e "${YELLOW}  If you see 'InconsistentClusterIdException', run: make kafka-reset${NC}"
        fi
    fi
    fi  # End of else block for infrastructure startup
    
    if [ "$INFRA_ONLY" = true ]; then
        echo -e "${GREEN}Infrastructure started. Use Ctrl+C to stop.${NC}"
        # Wait for interrupt
        while true; do sleep 1; done
    fi
fi

# Start Backend Services
if [ "$FRONTEND_ONLY" = false ]; then
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}Starting Backend Services${NC}"
    echo -e "${BLUE}========================================${NC}"
    
    # Check if virtual environment exists
    if [ ! -d "venv" ]; then
        echo -e "${RED}Error: Virtual environment not found. Please create it first:${NC}"
        echo "  python3 -m venv venv"
        echo "  source venv/bin/activate"
        echo "  pip install -r requirements.txt"
        exit 1
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Set Python path to include project root for imports
    export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"
    
    # Start Replay Service (port 8000)
    if check_port 8000; then
        echo -e "${YELLOW}⚠ Port 8000 is already in use. Skipping replay-service.${NC}"
    else
        echo -e "${BLUE}Starting replay-service on port 8000...${NC}"
        if [ "$RELOAD" = true ]; then
            # Use launcher script with reload
            (cd "$PROJECT_ROOT" && PYTHONPATH="$PROJECT_ROOT" python services/replay-service/run.py 8000 --reload) &
            REPLAY_PID=$!
            echo -e "${GREEN}✓ replay-service started (PID: $REPLAY_PID) with auto-reload${NC}"
        else
            (cd "$PROJECT_ROOT" && PYTHONPATH="$PROJECT_ROOT" python services/replay-service/run.py 8000) &
            REPLAY_PID=$!
            echo -e "${GREEN}✓ replay-service started (PID: $REPLAY_PID)${NC}"
        fi
    fi
    
    # Start Anomaly Service (no web server, just Kafka consumer)
    echo -e "${BLUE}Starting anomaly-service (Kafka consumer)...${NC}"
    (cd "$PROJECT_ROOT" && PYTHONPATH="$PROJECT_ROOT" python services/anomaly-service/run.py) &
    ANOMALY_PID=$!
    echo -e "${GREEN}✓ anomaly-service started (PID: $ANOMALY_PID)${NC}"
    echo -e "${YELLOW}  Note: anomaly-service is a Kafka consumer (no web server)${NC}"
    
    # Start Operator Service (port 8003)
    if check_port 8003; then
        echo -e "${YELLOW}⚠ Port 8003 is already in use. Skipping operator-service.${NC}"
    else
        echo -e "${BLUE}Starting operator-service on port 8003...${NC}"
        if [ "$RELOAD" = true ]; then
            # Use launcher script with reload
            (cd "$PROJECT_ROOT" && PYTHONPATH="$PROJECT_ROOT" python services/operator-service/run.py 8003 --reload) &
            OPERATOR_PID=$!
            echo -e "${GREEN}✓ operator-service started (PID: $OPERATOR_PID) with auto-reload${NC}"
        else
            (cd "$PROJECT_ROOT" && PYTHONPATH="$PROJECT_ROOT" python services/operator-service/run.py 8003) &
            OPERATOR_PID=$!
            echo -e "${GREEN}✓ operator-service started (PID: $OPERATOR_PID)${NC}"
        fi
    fi
    
    if [ "$BACKEND_ONLY" = true ]; then
        echo -e "\n${GREEN}Backend services started. Use Ctrl+C to stop.${NC}"
        # Wait for interrupt
        while true; do sleep 1; done
    fi
fi

# Start Frontend
if [ "$BACKEND_ONLY" = false ]; then
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}Starting Frontend${NC}"
    echo -e "${BLUE}========================================${NC}"
    
    if [ ! -d "ui/node_modules" ]; then
        echo -e "${YELLOW}⚠ node_modules not found. Installing dependencies...${NC}"
        cd ui
        npm install
        cd ..
    fi
    
    echo -e "${BLUE}Starting frontend dev server...${NC}"
    cd ui
    npm run dev &
    FRONTEND_PID=$!
    cd ..
    echo -e "${GREEN}✓ Frontend started (PID: $FRONTEND_PID) with hot reload${NC}"
    echo -e "${YELLOW}  Note: Frontend always runs with hot reload in dev mode${NC}"
    
    if [ "$FRONTEND_ONLY" = true ]; then
        echo -e "\n${GREEN}Frontend started. Use Ctrl+C to stop.${NC}"
        # Wait for interrupt
        while true; do sleep 1; done
    fi
fi

# Summary
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}All Services Started${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Services:${NC}"
echo -e "  ${GREEN}✓${NC} Infrastructure (Postgres, Kafka)"
if [ "$FRONTEND_ONLY" = false ]; then
    echo -e "  ${GREEN}✓${NC} replay-service (http://localhost:8000)"
    echo -e "  ${GREEN}✓${NC} anomaly-service (Kafka consumer)"
    echo -e "  ${GREEN}✓${NC} operator-service (http://localhost:8003)"
fi
if [ "$BACKEND_ONLY" = false ]; then
    echo -e "  ${GREEN}✓${NC} Frontend (http://localhost:5173)"
fi
if [ "$RELOAD" = true ]; then
    echo -e "\n${YELLOW}Auto-reload enabled for backend services${NC}"
fi
echo -e "\n${YELLOW}Press Ctrl+C to stop all services${NC}"

# Wait for all background processes
wait

