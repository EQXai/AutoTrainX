#!/bin/bash

# AutoTrainX Complete Stack Startup Script
# This script starts the entire AutoTrainX deployment stack

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
COMPOSE_FILES=()
PROFILES=()
ENVIRONMENT="${ENVIRONMENT:-production}"
MONITORING_ENABLED="${MONITORING_ENABLED:-true}"
BACKUP_ENABLED="${BACKUP_ENABLED:-true}"

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
    -e, --env ENV           Environment (development|staging|production)
    -p, --profile PROFILE   Docker Compose profile to enable
    --no-monitoring         Disable monitoring stack
    --no-backup             Disable backup services
    --api-only              Start only API services
    --monitoring-only       Start only monitoring services
    --stop                  Stop all services
    --restart               Restart all services
    --logs                  Show logs
    --status                Show service status

Examples:
    $0                          # Start full production stack
    $0 -e development           # Start development environment
    $0 -p comfyui               # Enable ComfyUI profile
    $0 --monitoring-only        # Start only monitoring
    $0 --stop                   # Stop all services
    $0 --logs                   # Show logs

EOF
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                usage
                exit 0
                ;;
            -e|--env)
                ENVIRONMENT="$2"
                shift 2
                ;;
            -p|--profile)
                PROFILES+=("$2")
                shift 2
                ;;
            --no-monitoring)
                MONITORING_ENABLED="false"
                shift
                ;;
            --no-backup)
                BACKUP_ENABLED="false"
                shift
                ;;
            --api-only)
                API_ONLY="true"
                shift
                ;;
            --monitoring-only)
                MONITORING_ONLY="true"
                shift
                ;;
            --stop)
                ACTION="stop"
                shift
                ;;
            --restart)
                ACTION="restart"
                shift
                ;;
            --logs)
                ACTION="logs"
                shift
                ;;
            --status)
                ACTION="status"
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done
}

setup_compose_files() {
    log_info "Setting up Docker Compose configuration..."
    
    # Base compose file
    COMPOSE_FILES+=("docker-compose.yml")
    
    # Environment-specific overrides
    case "$ENVIRONMENT" in
        development)
            if [[ -f "docker-compose.dev.yml" ]]; then
                COMPOSE_FILES+=("docker-compose.dev.yml")
            fi
            ;;
        staging)
            if [[ -f "docker-compose.staging.yml" ]]; then
                COMPOSE_FILES+=("docker-compose.staging.yml")
            fi
            ;;
        production)
            if [[ -f "docker-compose.prod.yml" ]]; then
                COMPOSE_FILES+=("docker-compose.prod.yml")
            fi
            ;;
    esac
    
    # Monitoring stack
    if [[ "$MONITORING_ENABLED" == "true" && "${MONITORING_ONLY:-false}" != "true" ]]; then
        COMPOSE_FILES+=("deploy/monitoring/docker-compose.monitoring.yml")
        PROFILES+=("monitoring")
    fi
    
    # Monitoring only
    if [[ "${MONITORING_ONLY:-false}" == "true" ]]; then
        COMPOSE_FILES=("deploy/monitoring/docker-compose.monitoring.yml")
    fi
    
    # API only
    if [[ "${API_ONLY:-false}" == "true" ]]; then
        COMPOSE_FILES=("docker-compose.yml")
    fi
    
    log_info "Compose files: ${COMPOSE_FILES[*]}"
    if [[ ${#PROFILES[@]} -gt 0 ]]; then
        log_info "Profiles: ${PROFILES[*]}"
    fi
}

build_compose_command() {
    local cmd="docker-compose"
    
    # Add compose files
    for file in "${COMPOSE_FILES[@]}"; do
        cmd="$cmd -f $file"
    done
    
    # Add profiles
    for profile in "${PROFILES[@]}"; do
        cmd="$cmd --profile $profile"
    done
    
    echo "$cmd"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        exit 1
    fi
    
    # Check environment file
    if [[ ! -f ".env" ]]; then
        if [[ -f ".env.example" ]]; then
            log_warning "No .env file found, copying from .env.example"
            cp .env.example .env
            log_warning "Please review and customize .env file"
        else
            log_error "No environment configuration found"
            exit 1
        fi
    fi
    
    log_success "Prerequisites check passed"
}

create_networks() {
    log_info "Creating Docker networks..."
    
    if ! docker network ls | grep -q "autotrainx-network"; then
        docker network create autotrainx-network --driver bridge --subnet=172.20.0.0/16
        log_success "Created autotrainx-network"
    else
        log_info "Network autotrainx-network already exists"
    fi
}

start_services() {
    log_info "Starting AutoTrainX services..."
    
    local compose_cmd=$(build_compose_command)
    
    # Pull latest images
    log_info "Pulling latest images..."
    $compose_cmd pull
    
    # Start services
    log_info "Starting services in detached mode..."
    $compose_cmd up -d
    
    # Wait for services to be ready
    log_info "Waiting for services to be ready..."
    sleep 30
    
    # Check service health
    check_service_health
    
    log_success "Services started successfully!"
}

stop_services() {
    log_info "Stopping AutoTrainX services..."
    
    local compose_cmd=$(build_compose_command)
    $compose_cmd down
    
    log_success "Services stopped"
}

restart_services() {
    log_info "Restarting AutoTrainX services..."
    
    stop_services
    sleep 5
    start_services
}

show_logs() {
    local compose_cmd=$(build_compose_command)
    $compose_cmd logs -f --tail=100
}

show_status() {
    log_info "Service Status:"
    
    local compose_cmd=$(build_compose_command)
    $compose_cmd ps
    
    echo
    log_info "Network Status:"
    docker network ls | grep autotrainx
    
    echo
    log_info "Volume Status:"
    docker volume ls | grep autotrainx
}

check_service_health() {
    log_info "Checking service health..."
    
    local services=("api:8000/health")
    
    if [[ "$MONITORING_ENABLED" == "true" ]]; then
        services+=("prometheus:9090/-/healthy")
        services+=("grafana:3000/api/health")
    fi
    
    for service in "${services[@]}"; do
        IFS=':' read -r container port_path <<< "$service"
        
        local max_attempts=10
        local attempt=0
        
        while [[ $attempt -lt $max_attempts ]]; do
            if curl -f -s "http://localhost:${port_path}" > /dev/null 2>&1; then
                log_success "$container is healthy"
                break
            fi
            
            log_info "Waiting for $container... ($((attempt + 1))/$max_attempts)"
            sleep 10
            ((attempt++))
        done
        
        if [[ $attempt -eq $max_attempts ]]; then
            log_warning "$container health check failed"
        fi
    done
}

show_endpoints() {
    log_info "Available endpoints:"
    
    echo "🚀 API Endpoints:"
    echo "  • API: http://localhost:8000"
    echo "  • API Docs: http://localhost:8000/docs"
    echo "  • Health Check: http://localhost:8000/health"
    
    if [[ "$MONITORING_ENABLED" == "true" ]]; then
        echo
        echo "📊 Monitoring Endpoints:"
        echo "  • Prometheus: http://localhost:9090"
        echo "  • Grafana: http://localhost:3000 (admin/admin)"
        echo "  • Alertmanager: http://localhost:9093"
    fi
    
    echo
    echo "📝 Log Management:"
    echo "  • View logs: $0 --logs"
    echo "  • Service status: $0 --status"
}

main() {
    cd "$PROJECT_ROOT"
    
    parse_args "$@"
    check_prerequisites
    setup_compose_files
    create_networks
    
    case "${ACTION:-start}" in
        start)
            start_services
            show_endpoints
            ;;
        stop)
            stop_services
            ;;
        restart)
            restart_services
            show_endpoints
            ;;
        logs)
            show_logs
            ;;
        status)
            show_status
            ;;
        *)
            log_error "Unknown action: ${ACTION}"
            exit 1
            ;;
    esac
}

# Handle script interruption
trap 'log_error "Script interrupted"; exit 1' INT TERM

# Run main function
main "$@"