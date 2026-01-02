#!/usr/bin/env python3
"""
Infrastructure Health Check Script

Checks the health of all infrastructure components:
- Kafka
- Zookeeper
- Postgres
- Verifies psql connection works
- Checks for container restart loops
"""

import sys
import subprocess
import time
from typing import Tuple, Optional

# Container names
CONTAINERS = {
    'postgres': 'fleetops-postgres',
    'zookeeper': 'fleetops-zookeeper',
    'kafka': 'fleetops-kafka'
}

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'
BOLD = '\033[1m'


def run_command(cmd: list, capture_output: bool = True) -> Tuple[int, str, str]:
    """Run a shell command and return exit code, stdout, stderr."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=capture_output,
            text=True,
            timeout=10
        )
        stdout = result.stdout.strip() if capture_output else ""
        stderr = result.stderr.strip() if capture_output else ""
        return result.returncode, stdout, stderr
    except subprocess.TimeoutExpired:
        return 1, "", "Command timed out"
    except Exception as e:
        return 1, "", str(e)


def check_container_exists(container_name: str) -> bool:
    """Check if container exists."""
    exit_code, _, _ = run_command(['docker', 'ps', '-a', '--filter', f'name={container_name}', '--format', '{{.Names}}'])
    return exit_code == 0


def check_container_running(container_name: str) -> bool:
    """Check if container is running."""
    exit_code, output, _ = run_command(['docker', 'ps', '--filter', f'name={container_name}', '--format', '{{.Names}}'])
    return exit_code == 0 and container_name in output


def get_container_health(container_name: str) -> Optional[str]:
    """Get container health status."""
    exit_code, output, _ = run_command([
        'docker', 'inspect', '--format', '{{.State.Health.Status}}', container_name
    ])
    if exit_code == 0 and output:
        return output.strip()
    return None


def get_restart_count(container_name: str) -> int:
    """Get container restart count."""
    exit_code, output, _ = run_command([
        'docker', 'inspect', '--format', '{{.RestartCount}}', container_name
    ])
    if exit_code == 0 and output:
        try:
            return int(output.strip())
        except ValueError:
            return 0
    return 0


def check_postgres_health() -> Tuple[bool, str]:
    """Check Postgres health."""
    container_name = CONTAINERS['postgres']
    
    if not check_container_exists(container_name):
        return False, "Container does not exist"
    
    if not check_container_running(container_name):
        return False, "Container is not running"
    
    health_status = get_container_health(container_name)
    if health_status == 'healthy':
        return True, "Healthy"
    elif health_status == 'starting':
        return False, "Starting (not ready yet)"
    elif health_status == 'unhealthy':
        return False, "Unhealthy"
    else:
        # Try direct connection test
        exit_code, _, _ = run_command([
            'docker', 'exec', container_name, 'pg_isready', '-U', 'postgres'
        ])
        if exit_code == 0:
            return True, "Running (healthcheck not configured)"
        return False, f"Unknown status: {health_status or 'no healthcheck'}"


def check_zookeeper_health() -> Tuple[bool, str]:
    """Check Zookeeper health."""
    container_name = CONTAINERS['zookeeper']
    
    if not check_container_exists(container_name):
        return False, "Container does not exist"
    
    if not check_container_running(container_name):
        return False, "Container is not running"
    
    health_status = get_container_health(container_name)
    if health_status == 'healthy':
        return True, "Healthy"
    elif health_status == 'starting':
        return False, "Starting (not ready yet)"
    elif health_status == 'unhealthy':
        return False, "Unhealthy"
    else:
        # Try direct connection test
        exit_code, _, _ = run_command([
            'docker', 'exec', container_name, 'nc', '-z', 'localhost', '2181'
        ])
        if exit_code == 0:
            return True, "Running (healthcheck not configured)"
        return False, f"Unknown status: {health_status or 'no healthcheck'}"


def check_kafka_health() -> Tuple[bool, str]:
    """Check Kafka health."""
    container_name = CONTAINERS['kafka']
    
    if not check_container_exists(container_name):
        return False, "Container does not exist"
    
    if not check_container_running(container_name):
        return False, "Container is not running"
    
    health_status = get_container_health(container_name)
    if health_status == 'healthy':
        return True, "Healthy"
    elif health_status == 'starting':
        return False, "Starting (not ready yet)"
    elif health_status == 'unhealthy':
        return False, "Unhealthy"
    else:
        # Try direct connection test
        exit_code, _, _ = run_command([
            'docker', 'exec', container_name,
            'kafka-broker-api-versions', '--bootstrap-server', 'localhost:9092'
        ])
        if exit_code == 0:
            return True, "Running (healthcheck not configured)"
        return False, f"Unknown status: {health_status or 'no healthcheck'}"


def check_psql_connection() -> Tuple[bool, str]:
    """Check if psql connection works."""
    container_name = CONTAINERS['postgres']
    
    if not check_container_running(container_name):
        return False, "Postgres container is not running"
    
    # Try to connect and run a simple query
    exit_code, output, error = run_command([
        'docker', 'exec', container_name,
        'psql', '-U', 'postgres', '-d', 'fleetops', '-c', 'SELECT 1;'
    ])
    
    if exit_code == 0:
        return True, "Connection successful"
    else:
        return False, f"Connection failed: {error or output}"


def check_restart_loops() -> Tuple[bool, dict]:
    """Check for container restart loops."""
    restart_counts = {}
    has_loops = False
    
    for service, container_name in CONTAINERS.items():
        if check_container_exists(container_name):
            count = get_restart_count(container_name)
            restart_counts[service] = count
            if count > 5:  # More than 5 restarts suggests a loop
                has_loops = True
    
    return not has_loops, restart_counts


def print_status(service: str, is_healthy: bool, message: str):
    """Print status with color coding."""
    status = f"{GREEN}✓ PASS{RESET}" if is_healthy else f"{RED}✗ FAIL{RESET}"
    print(f"  {status} {BOLD}{service}:{RESET} {message}")


def main():
    """Main health check function."""
    print(f"{BOLD}Infrastructure Health Check{RESET}")
    print("=" * 60)
    print()
    
    all_healthy = True
    results = {}
    
    # Check Postgres
    print(f"{BOLD}Checking Postgres...{RESET}")
    is_healthy, message = check_postgres_health()
    print_status("Postgres", is_healthy, message)
    results['postgres'] = (is_healthy, message)
    if not is_healthy:
        all_healthy = False
    print()
    
    # Check Zookeeper
    print(f"{BOLD}Checking Zookeeper...{RESET}")
    is_healthy, message = check_zookeeper_health()
    print_status("Zookeeper", is_healthy, message)
    results['zookeeper'] = (is_healthy, message)
    if not is_healthy:
        all_healthy = False
    print()
    
    # Check Kafka
    print(f"{BOLD}Checking Kafka...{RESET}")
    is_healthy, message = check_kafka_health()
    print_status("Kafka", is_healthy, message)
    results['kafka'] = (is_healthy, message)
    if not is_healthy:
        all_healthy = False
    print()
    
    # Check psql connection
    print(f"{BOLD}Checking psql connection...{RESET}")
    is_healthy, message = check_psql_connection()
    print_status("psql", is_healthy, message)
    results['psql'] = (is_healthy, message)
    if not is_healthy:
        all_healthy = False
    print()
    
    # Check restart loops
    print(f"{BOLD}Checking for restart loops...{RESET}")
    no_loops, restart_counts = check_restart_loops()
    if no_loops:
        print_status("Restart loops", True, "No restart loops detected")
        for service, count in restart_counts.items():
            if count > 0:
                print(f"    {YELLOW}Note:{RESET} {service} has restarted {count} time(s)")
    else:
        print_status("Restart loops", False, "Potential restart loops detected")
        for service, count in restart_counts.items():
            if count > 5:
                print(f"    {RED}Warning:{RESET} {service} has restarted {count} times")
        all_healthy = False
    results['restart_loops'] = (no_loops, restart_counts)
    print()
    
    # Summary
    print("=" * 60)
    if all_healthy:
        print(f"{GREEN}{BOLD}✓ All checks passed!{RESET}")
        return 0
    else:
        print(f"{RED}{BOLD}✗ Some checks failed{RESET}")
        print()
        print("Failed checks:")
        for service, (is_healthy, message) in results.items():
            if not is_healthy:
                print(f"  - {service}: {message}")
        return 1


if __name__ == '__main__':
    sys.exit(main())

