#!/bin/bash
# Complete demo script - starts everything and launches the demo
# Usage: ./scripts/run_demo.sh [--no-frontend] [--skip-infra]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Parse arguments
NO_FRONTEND=false
SKIP_INFRA=false
for arg in "$@"; do
    case $arg in
        --no-frontend)
            NO_FRONTEND=true
            shift
            ;;
        --skip-infra)
            SKIP_INFRA=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --no-frontend    Don't start the frontend UI"
            echo "  --skip-infra     Skip infrastructure startup (assumes already running)"
            echo "  --help, -h       Show this help message"
            exit 0
            ;;
    esac
done

# Get project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# Log files
REPLAY_LOG="/tmp/replay-service.log"
ANOMALY_LOG="/tmp/anomaly-service.log"
OPERATOR_LOG="/tmp/operator-service.log"

# Function to print section header
print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

# Function to check if a port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        return 0
    else
        return 1
    fi
}

# Function to wait for HTTP service
wait_for_http() {
    local url=$1
    local service_name=$2
    local max_attempts=30
    local attempt=1
    
    echo -e "${BLUE}Waiting for $service_name...${NC}"
    while [ $attempt -le $max_attempts ]; do
        if curl -s "$url" > /dev/null 2>&1; then
            echo -e "${GREEN}✓ $service_name is ready!${NC}"
            return 0
        fi
        sleep 1
        attempt=$((attempt + 1))
    done
    
    echo -e "${RED}✗ $service_name failed to start${NC}"
    return 1
}

# Function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}Shutting down services...${NC}"
    
    # Stop replay if running
    curl -s -X POST http://localhost:8000/replay/stop > /dev/null 2>&1 || true
    
    # Kill backend services
    pkill -f "replay-service/run.py" 2>/dev/null || true
    pkill -f "anomaly-service/run.py" 2>/dev/null || true
    pkill -f "operator-service/run.py" 2>/dev/null || true
    
    echo -e "${GREEN}Backend services stopped${NC}"
    if [ "$SKIP_INFRA" = false ]; then
        echo -e "${YELLOW}Infrastructure (Postgres, Kafka) is still running${NC}"
        echo -e "${YELLOW}To stop infrastructure: make down${NC}"
    fi
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Start Infrastructure
if [ "$SKIP_INFRA" = false ]; then
    print_header "Starting Infrastructure"
    
    # Check Docker
    if ! docker info > /dev/null 2>&1; then
        echo -e "${RED}Error: Docker daemon is not running. Please start Docker Desktop and try again.${NC}"
        exit 1
    fi
    
    # Check if already running
    if docker ps --format '{{.Names}}' | grep -q "^fleetops-postgres$" && \
       docker ps --format '{{.Names}}' | grep -q "^fleetops-kafka$"; then
        echo -e "${GREEN}✓ Infrastructure is already running${NC}"
    else
        echo -e "${BLUE}Starting Postgres, Zookeeper, and Kafka...${NC}"
        docker-compose up -d
        
        # Wait for Postgres
        max_wait=60
        elapsed=0
        while [ $elapsed -lt $max_wait ]; do
            if docker inspect --format='{{.State.Health.Status}}' fleetops-postgres 2>/dev/null | grep -q "healthy"; then
                echo -e "${GREEN}✓ Postgres is healthy${NC}"
                break
            fi
            sleep 2
            elapsed=$((elapsed + 2))
        done
        
        # Wait for Kafka
        max_wait=90
        elapsed=0
        while [ $elapsed -lt $max_wait ]; do
            if docker inspect --format='{{.State.Health.Status}}' fleetops-kafka 2>/dev/null | grep -q "healthy"; then
                echo -e "${GREEN}✓ Kafka is healthy${NC}"
                break
            fi
            if [ $((elapsed % 10)) -eq 0 ] && [ $elapsed -gt 0 ]; then
                echo -e "${YELLOW}  Waiting for Kafka... (${elapsed}s/${max_wait}s)${NC}"
            fi
            sleep 2
            elapsed=$((elapsed + 2))
        done
    fi
else
    echo -e "${YELLOW}Skipping infrastructure startup (assuming already running)${NC}"
fi

# Check virtual environment
if [ ! -d "venv" ]; then
    echo -e "${RED}Error: Virtual environment not found. Please create it first:${NC}"
    echo "  python3 -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

# Start Backend Services
print_header "Starting Backend Services"

# Kill any existing services
pkill -f "replay-service/run.py" 2>/dev/null || true
pkill -f "anomaly-service/run.py" 2>/dev/null || true
pkill -f "operator-service/run.py" 2>/dev/null || true
sleep 2

# Start Replay Service
if check_port 8000; then
    echo -e "${YELLOW}⚠ Port 8000 is already in use. Killing existing process...${NC}"
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    sleep 2
fi

echo -e "${BLUE}Starting replay-service on port 8000...${NC}"
python services/replay-service/run.py 8000 > "$REPLAY_LOG" 2>&1 &
REPLAY_PID=$!
echo -e "${GREEN}✓ replay-service started (PID: $REPLAY_PID)${NC}"

# Start Anomaly Service
echo -e "${BLUE}Starting anomaly-service...${NC}"
python services/anomaly-service/run.py > "$ANOMALY_LOG" 2>&1 &
ANOMALY_PID=$!
echo -e "${GREEN}✓ anomaly-service started (PID: $ANOMALY_PID)${NC}"

# Start Operator Service
if check_port 8003; then
    echo -e "${YELLOW}⚠ Port 8003 is already in use. Killing existing process...${NC}"
    lsof -ti:8003 | xargs kill -9 2>/dev/null || true
    sleep 2
fi

echo -e "${BLUE}Starting operator-service on port 8003...${NC}"
python services/operator-service/run.py 8003 > "$OPERATOR_LOG" 2>&1 &
OPERATOR_PID=$!
echo -e "${GREEN}✓ operator-service started (PID: $OPERATOR_PID)${NC}"

# Wait for services to be ready
echo -e "\n${BLUE}Waiting for services to be ready...${NC}"
wait_for_http "http://localhost:8000/health" "replay-service" || {
    echo -e "${RED}replay-service failed to start. Check logs: tail -f $REPLAY_LOG${NC}"
    exit 1
}

wait_for_http "http://localhost:8003/health" "operator-service" || {
    echo -e "${RED}operator-service failed to start. Check logs: tail -f $OPERATOR_LOG${NC}"
    exit 1
}

# Give anomaly service a moment to connect to Kafka
sleep 3

# Prepare Database
print_header "Preparing Database"

echo -e "${BLUE}Clearing old alerts and vehicle states...${NC}"
docker-compose exec -T postgres psql -U postgres -d fleetops <<EOF > /dev/null 2>&1 || true
DELETE FROM alerts;
DELETE FROM operator_actions;
DELETE FROM vehicle_state;
EOF
echo -e "${GREEN}✓ Database cleared${NC}"

# Start Demo Replay
print_header "Starting Demo Replay"

echo -e "${BLUE}Starting demo replay at 1 Hz...${NC}"
DEMO_RESPONSE=$(curl -s -X POST http://localhost:8000/demo/start)
if echo "$DEMO_RESPONSE" | grep -q "started"; then
    echo -e "${GREEN}✓ Demo replay started${NC}"
    echo -e "${CYAN}$DEMO_RESPONSE${NC}"
else
    echo -e "${RED}✗ Failed to start demo replay${NC}"
    echo "$DEMO_RESPONSE"
    exit 1
fi

# Start Frontend (optional)
if [ "$NO_FRONTEND" = false ]; then
    print_header "Starting Frontend"
    
    if [ ! -d "ui/node_modules" ]; then
        echo -e "${YELLOW}⚠ node_modules not found. Installing dependencies...${NC}"
        cd ui
        npm install
        cd ..
    fi
    
    echo -e "${BLUE}Starting frontend dev server...${NC}"
    cd ui
    npm run dev > /dev/null 2>&1 &
    FRONTEND_PID=$!
    cd ..
    echo -e "${GREEN}✓ Frontend started (PID: $FRONTEND_PID)${NC}"
    echo -e "${CYAN}  Frontend URL: http://localhost:5173${NC}"
fi

# Summary
print_header "Demo Started Successfully"

echo -e "${GREEN}Services:${NC}"
echo -e "  ${GREEN}✓${NC} Infrastructure (Postgres, Kafka)"
echo -e "  ${GREEN}✓${NC} replay-service (http://localhost:8000)"
echo -e "  ${GREEN}✓${NC} anomaly-service (Kafka consumer)"
echo -e "  ${GREEN}✓${NC} operator-service (http://localhost:8003)"
if [ "$NO_FRONTEND" = false ]; then
    echo -e "  ${GREEN}✓${NC} Frontend (http://localhost:5173)"
fi

echo -e "\n${CYAN}Demo Status:${NC}"
echo -e "  ${CYAN}•${NC} Replay running at 1 Hz (demo mode)"
echo -e "  ${CYAN}•${NC} Alerts streaming in real-time"
echo -e "  ${CYAN}•${NC} Human-readable IDs enabled (VH-XXXX, INC-XXXX)"

if [ "$NO_FRONTEND" = false ]; then
    echo -e "\n${YELLOW}Open your browser to: ${CYAN}http://localhost:5173${NC}"
fi

echo -e "\n${YELLOW}Useful commands:${NC}"
echo -e "  ${CYAN}•${NC} Check replay status: curl http://localhost:8000/replay/status"
echo -e "  ${CYAN}•${NC} Stop replay: curl -X POST http://localhost:8000/replay/stop"
echo -e "  ${CYAN}•${NC} View logs: tail -f $REPLAY_LOG"
echo -e "  ${CYAN}•${NC} View alerts: docker-compose exec postgres psql -U postgres -d fleetops -c 'SELECT COUNT(*) FROM alerts;'"

echo -e "\n${YELLOW}Press Ctrl+C to stop all services${NC}"

# Monitor replay status
while true; do
    sleep 10
    STATUS=$(curl -s http://localhost:8000/replay/status 2>/dev/null || echo '{"active":false}')
    if echo "$STATUS" | grep -q '"active":false'; then
        echo -e "\n${YELLOW}Replay has completed. Demo finished.${NC}"
        break
    fi
done

# Keep script running
wait
