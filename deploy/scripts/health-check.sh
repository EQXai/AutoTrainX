#!/bin/bash

# AutoTrainX Health Check Script
# Comprehensive health monitoring for the AutoTrainX API deployment

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
API_URL="${API_URL:-http://localhost:8000}"
TIMEOUT="${TIMEOUT:-30}"
VERBOSE="${VERBOSE:-false}"
ALERTS_ENABLED="${ALERTS_ENABLED:-false}"
SLACK_WEBHOOK="${SLACK_WEBHOOK:-}"
EMAIL_RECIPIENTS="${EMAIL_RECIPIENTS:-}"

# Health check results
declare -A HEALTH_STATUS
OVERALL_HEALTHY=true

# Functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Options:
    -h, --help              Show this help message
    -u, --url URL           API base URL (default: http://localhost:8000)
    -t, --timeout SECONDS   Request timeout (default: 30)
    -v, --verbose           Enable verbose output
    -a, --alerts            Enable alert notifications
    --slack-webhook URL     Slack webhook for notifications
    --email RECIPIENTS      Email recipients for alerts (comma-separated)

Examples:
    $0                                    # Basic health check
    $0 -v                                # Verbose output
    $0 -u https://api.example.com        # Custom API URL
    $0 -a --slack-webhook https://...    # Enable Slack alerts

EOF
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                usage
                exit 0
                ;;
            -u|--url)
                API_URL="$2"
                shift 2
                ;;
            -t|--timeout)
                TIMEOUT="$2"
                shift 2
                ;;
            -v|--verbose)
                VERBOSE="true"
                shift
                ;;
            -a|--alerts)
                ALERTS_ENABLED="true"
                shift
                ;;
            --slack-webhook)
                SLACK_WEBHOOK="$2"
                shift 2
                ;;
            --email)
                EMAIL_RECIPIENTS="$2"
                shift 2
                ;;
            *)
                log_error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done
}

check_api_health() {
    log_info "Checking API health endpoint..."
    
    local health_url="$API_URL/health"
    local response
    local status_code
    
    if response=$(curl -s -w "%{http_code}" --max-time "$TIMEOUT" "$health_url" 2>/dev/null); then
        status_code="${response: -3}"
        response="${response%???}"
        
        if [[ "$status_code" == "200" ]]; then
            if echo "$response" | jq -e '.status == "healthy"' > /dev/null 2>&1; then
                HEALTH_STATUS["api"]="healthy"
                log_success "API health check passed"
                
                if [[ "$VERBOSE" == "true" ]]; then
                    echo "$response" | jq .
                fi
            else
                HEALTH_STATUS["api"]="degraded"
                log_warning "API reports unhealthy status: $response"
                OVERALL_HEALTHY=false
            fi
        else
            HEALTH_STATUS["api"]="unhealthy"
            log_error "API health check failed with status $status_code"
            OVERALL_HEALTHY=false
        fi
    else
        HEALTH_STATUS["api"]="unreachable"
        log_error "Cannot reach API health endpoint"
        OVERALL_HEALTHY=false
    fi
}

check_api_endpoints() {
    log_info "Testing API endpoints..."
    
    local endpoints=(
        "GET:/:200"
        "GET:/docs:200"
        "GET:/openapi.json:200"
        "GET:/api/v1/jobs:200"
        "GET:/api/v1/presets:200"
    )
    
    local failed=0
    
    for endpoint in "${endpoints[@]}"; do
        IFS=':' read -r method path expected_code <<< "$endpoint"
        
        local url="$API_URL$path"
        local status_code
        
        if [[ "$VERBOSE" == "true" ]]; then
            log_info "Testing $method $path"
        fi
        
        case "$method" in
            GET)
                status_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time "$TIMEOUT" "$url" 2>/dev/null || echo "000")
                ;;
            POST)
                status_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time "$TIMEOUT" -X POST "$url" 2>/dev/null || echo "000")
                ;;
        esac
        
        if [[ "$status_code" == "$expected_code" ]]; then
            if [[ "$VERBOSE" == "true" ]]; then
                log_success "$method $path: $status_code"
            fi
        else
            log_warning "$method $path: Expected $expected_code, got $status_code"
            ((failed++))
        fi
    done
    
    if [[ $failed -eq 0 ]]; then
        HEALTH_STATUS["endpoints"]="healthy"
        log_success "All API endpoints responsive"
    else
        HEALTH_STATUS["endpoints"]="degraded"
        log_warning "$failed endpoint(s) failed"
        OVERALL_HEALTHY=false
    fi
}

check_docker_containers() {
    log_info "Checking Docker containers..."
    
    if ! command -v docker-compose &> /dev/null; then
        HEALTH_STATUS["containers"]="unknown"
        log_warning "docker-compose not available, skipping container check"
        return
    fi
    
    local compose_file="/opt/autotrainx/docker-compose.yml"
    if [[ ! -f "$compose_file" ]]; then
        HEALTH_STATUS["containers"]="unknown"
        log_warning "Docker compose file not found, skipping container check"
        return
    fi
    
    local failed_containers=()
    local services=(api redis)
    
    for service in "${services[@]}"; do
        if docker-compose -f "$compose_file" ps -q "$service" > /dev/null 2>&1; then
            local container_id=$(docker-compose -f "$compose_file" ps -q "$service")
            local status=$(docker inspect --format '{{.State.Status}}' "$container_id" 2>/dev/null || echo "unknown")
            
            if [[ "$status" == "running" ]]; then
                if [[ "$VERBOSE" == "true" ]]; then
                    log_success "Container $service: running"
                fi
            else
                log_error "Container $service: $status"
                failed_containers+=("$service")
            fi
        else
            log_error "Container $service: not found"
            failed_containers+=("$service")
        fi
    done
    
    if [[ ${#failed_containers[@]} -eq 0 ]]; then
        HEALTH_STATUS["containers"]="healthy"
        log_success "All containers running"
    else
        HEALTH_STATUS["containers"]="unhealthy"
        log_error "Failed containers: ${failed_containers[*]}"
        OVERALL_HEALTHY=false
    fi
}

check_database() {
    log_info "Checking database connection..."
    
    local db_check_url="$API_URL/api/v1/jobs"
    local response
    local status_code
    
    if response=$(curl -s -w "%{http_code}" --max-time "$TIMEOUT" "$db_check_url" 2>/dev/null); then
        status_code="${response: -3}"
        
        if [[ "$status_code" == "200" ]]; then
            HEALTH_STATUS["database"]="healthy"
            log_success "Database connection healthy"
        else
            HEALTH_STATUS["database"]="unhealthy"
            log_error "Database check failed with status $status_code"
            OVERALL_HEALTHY=false
        fi
    else
        HEALTH_STATUS["database"]="unreachable"
        log_error "Cannot check database connection"
        OVERALL_HEALTHY=false
    fi
}

check_disk_space() {
    log_info "Checking disk space..."
    
    local critical_paths=("/opt/autotrainx" "/var/log" "/" "/tmp")
    local failed=0
    
    for path in "${critical_paths[@]}"; do
        if [[ -d "$path" ]]; then
            local usage=$(df "$path" | awk 'NR==2 {print $5}' | sed 's/%//')
            
            if [[ $usage -ge 90 ]]; then
                log_error "Disk space critical on $path: ${usage}%"
                ((failed++))
            elif [[ $usage -ge 80 ]]; then
                log_warning "Disk space high on $path: ${usage}%"
            elif [[ "$VERBOSE" == "true" ]]; then
                log_info "Disk space on $path: ${usage}%"
            fi
        fi
    done
    
    if [[ $failed -eq 0 ]]; then
        HEALTH_STATUS["disk"]="healthy"
        log_success "Disk space check passed"
    else
        HEALTH_STATUS["disk"]="critical"
        OVERALL_HEALTHY=false
    fi
}

check_memory_usage() {
    log_info "Checking memory usage..."
    
    local memory_info=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
    
    if [[ $memory_info -ge 90 ]]; then
        HEALTH_STATUS["memory"]="critical"
        log_error "Memory usage critical: ${memory_info}%"
        OVERALL_HEALTHY=false
    elif [[ $memory_info -ge 80 ]]; then
        HEALTH_STATUS["memory"]="warning"
        log_warning "Memory usage high: ${memory_info}%"
    else
        HEALTH_STATUS["memory"]="healthy"
        if [[ "$VERBOSE" == "true" ]]; then
            log_info "Memory usage: ${memory_info}%"
        fi
    fi
}

check_websocket_connection() {
    log_info "Testing WebSocket connection..."
    
    # Simple WebSocket test using Python if available
    if command -v python3 &> /dev/null; then
        local ws_url="${API_URL/http/ws}/ws/progress"
        local ws_test_result
        
        ws_test_result=$(python3 -c "
import asyncio
import websockets
import sys
import json
from urllib.parse import urlparse

async def test_websocket():
    uri = '$ws_url'
    try:
        async with websockets.connect(uri, timeout=5) as websocket:
            # Send a test message
            await websocket.send(json.dumps({'type': 'ping'}))
            # Try to receive a response (with timeout)
            response = await asyncio.wait_for(websocket.recv(), timeout=5)
            return True
    except Exception as e:
        return False

try:
    result = asyncio.run(test_websocket())
    print('success' if result else 'failed')
except Exception:
    print('failed')
" 2>/dev/null || echo "failed")
        
        if [[ "$ws_test_result" == "success" ]]; then
            HEALTH_STATUS["websocket"]="healthy"
            log_success "WebSocket connection test passed"
        else
            HEALTH_STATUS["websocket"]="unhealthy"
            log_warning "WebSocket connection test failed"
        fi
    else
        HEALTH_STATUS["websocket"]="skipped"
        if [[ "$VERBOSE" == "true" ]]; then
            log_info "Python3 not available, skipping WebSocket test"
        fi
    fi
}

generate_health_report() {
    echo
    log_info "=== Health Check Summary ==="
    
    for component in "${!HEALTH_STATUS[@]}"; do
        local status="${HEALTH_STATUS[$component]}"
        case "$status" in
            healthy)
                echo -e "${GREEN}✓${NC} $component: $status"
                ;;
            warning|degraded)
                echo -e "${YELLOW}⚠${NC} $component: $status"
                ;;
            unhealthy|critical)
                echo -e "${RED}✗${NC} $component: $status"
                ;;
            *)
                echo -e "${BLUE}?${NC} $component: $status"
                ;;
        esac
    done
    
    echo
    if [[ "$OVERALL_HEALTHY" == "true" ]]; then
        log_success "Overall Status: HEALTHY"
    else
        log_error "Overall Status: UNHEALTHY"
    fi
}

send_alerts() {
    if [[ "$ALERTS_ENABLED" != "true" || "$OVERALL_HEALTHY" == "true" ]]; then
        return 0
    fi
    
    local message="🚨 AutoTrainX Health Check Alert\n\nUnhealthy components detected:\n"
    
    for component in "${!HEALTH_STATUS[@]}"; do
        local status="${HEALTH_STATUS[$component]}"
        if [[ "$status" != "healthy" && "$status" != "skipped" ]]; then
            message+="\n• $component: $status"
        fi
    done
    
    message+="\n\nTimestamp: $(date)"
    message+="\nServer: $(hostname)"
    
    # Send Slack notification
    if [[ -n "$SLACK_WEBHOOK" ]]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"$message\"}" \
            "$SLACK_WEBHOOK" &> /dev/null || true
    fi
    
    # Send email notification
    if [[ -n "$EMAIL_RECIPIENTS" ]] && command -v mail &> /dev/null; then
        echo -e "$message" | mail -s "AutoTrainX Health Alert" "$EMAIL_RECIPIENTS" || true
    fi
}

main() {
    parse_args "$@"
    
    log_info "Starting AutoTrainX health check..."
    log_info "API URL: $API_URL"
    log_info "Timeout: ${TIMEOUT}s"
    
    # Run health checks
    check_api_health
    check_api_endpoints
    check_docker_containers
    check_database
    check_disk_space
    check_memory_usage
    check_websocket_connection
    
    # Generate report
    generate_health_report
    
    # Send alerts if needed
    send_alerts
    
    # Exit with appropriate code
    if [[ "$OVERALL_HEALTHY" == "true" ]]; then
        exit 0
    else
        exit 1
    fi
}

# Run main function
main "$@"