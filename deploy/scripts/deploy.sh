#!/bin/bash

# AutoTrainX Production Deployment Script
# This script handles building, testing, and deploying the AutoTrainX API

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
BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
VERSION="${VERSION:-$(git describe --tags --always 2>/dev/null || echo "dev")}"
VCS_REF="${VCS_REF:-$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")}"
DOCKER_REGISTRY="${DOCKER_REGISTRY:-}"
DEPLOY_ENV="${DEPLOY_ENV:-production}"
SKIP_TESTS="${SKIP_TESTS:-false}"
BACKUP_BEFORE_DEPLOY="${BACKUP_BEFORE_DEPLOY:-true}"
ROLLBACK_ON_FAILURE="${ROLLBACK_ON_FAILURE:-true}"

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
    -v, --version VERSION   Set version tag (default: git describe)
    -e, --env ENV           Deployment environment (default: production)
    -r, --registry REGISTRY Docker registry URL
    --skip-tests            Skip running tests
    --no-backup             Skip backup before deployment
    --no-rollback           Don't rollback on failure
    --build-only            Only build images, don't deploy
    --deploy-only           Only deploy, don't build

Examples:
    $0                      # Full deployment with defaults
    $0 -v 1.2.3 -e staging # Deploy version 1.2.3 to staging
    $0 --skip-tests         # Deploy without running tests
    $0 --build-only         # Only build Docker images

EOF
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                usage
                exit 0
                ;;
            -v|--version)
                VERSION="$2"
                shift 2
                ;;
            -e|--env)
                DEPLOY_ENV="$2"
                shift 2
                ;;
            -r|--registry)
                DOCKER_REGISTRY="$2"
                shift 2
                ;;
            --skip-tests)
                SKIP_TESTS="true"
                shift
                ;;
            --no-backup)
                BACKUP_BEFORE_DEPLOY="false"
                shift
                ;;
            --no-rollback)
                ROLLBACK_ON_FAILURE="false"
                shift
                ;;
            --build-only)
                BUILD_ONLY="true"
                shift
                ;;
            --deploy-only)
                DEPLOY_ONLY="true"
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

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check required commands
    local commands=("docker" "docker-compose" "git")
    for cmd in "${commands[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            log_error "Required command '$cmd' not found"
            exit 1
        fi
    done
    
    # Check Docker daemon
    if ! docker info &> /dev/null; then
        log_error "Docker daemon not accessible"
        exit 1
    fi
    
    # Check if we're in a git repository
    if ! git rev-parse --git-dir &> /dev/null; then
        log_warning "Not in a git repository. Version info may be limited."
    fi
    
    log_success "Prerequisites check passed"
}

run_tests() {
    if [[ "$SKIP_TESTS" == "true" ]]; then
        log_warning "Skipping tests as requested"
        return 0
    fi
    
    log_info "Running tests..."
    
    cd "$PROJECT_ROOT"
    
    # Create test environment if it doesn't exist
    if [[ ! -f "docker-compose.test.yml" ]]; then
        log_warning "No test configuration found, creating basic test setup"
        cat > docker-compose.test.yml << EOF
version: '3.8'
services:
  api-test:
    build:
      context: .
      dockerfile: Dockerfile
      target: development
    environment:
      - ENVIRONMENT=test
      - DATABASE_URL=sqlite:///tmp/test.db
    command: pytest tests/ -v --cov=api --cov-report=term-missing
    volumes:
      - ./tests:/app/tests
      - ./api:/app/api
      - ./src:/app/src
EOF
    fi
    
    # Run tests
    if ! docker-compose -f docker-compose.test.yml run --rm api-test; then
        log_error "Tests failed!"
        return 1
    fi
    
    # Cleanup test containers
    docker-compose -f docker-compose.test.yml down -v
    
    log_success "All tests passed"
}

build_images() {
    log_info "Building Docker images..."
    
    cd "$PROJECT_ROOT"
    
    # Set image tags
    local image_name="autotrainx-api"
    local full_tag="${image_name}:${VERSION}"
    
    if [[ -n "$DOCKER_REGISTRY" ]]; then
        full_tag="${DOCKER_REGISTRY}/${full_tag}"
    fi
    
    # Build the image
    log_info "Building image: $full_tag"
    docker build \
        --target production \
        --build-arg BUILD_DATE="$BUILD_DATE" \
        --build-arg VERSION="$VERSION" \
        --build-arg VCS_REF="$VCS_REF" \
        -t "$full_tag" \
        -t "${image_name}:latest" \
        .
    
    # Tag for registry if specified
    if [[ -n "$DOCKER_REGISTRY" ]]; then
        docker tag "$full_tag" "${DOCKER_REGISTRY}/${image_name}:latest"
        log_info "Tagged for registry: ${DOCKER_REGISTRY}/${image_name}:latest"
    fi
    
    log_success "Docker images built successfully"
    
    # Show image size
    docker images "$image_name" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"
}

push_images() {
    if [[ -z "$DOCKER_REGISTRY" ]]; then
        log_info "No registry specified, skipping image push"
        return 0
    fi
    
    log_info "Pushing images to registry..."
    
    local image_name="autotrainx-api"
    
    # Push versioned image
    docker push "${DOCKER_REGISTRY}/${image_name}:${VERSION}"
    
    # Push latest tag
    docker push "${DOCKER_REGISTRY}/${image_name}:latest"
    
    log_success "Images pushed to registry"
}

backup_current_state() {
    if [[ "$BACKUP_BEFORE_DEPLOY" != "true" ]]; then
        log_info "Backup disabled, skipping"
        return 0
    fi
    
    log_info "Creating backup before deployment..."
    
    local backup_dir="/opt/autotrainx/backups/pre-deploy"
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_name="backup_${timestamp}_v${VERSION}"
    
    mkdir -p "$backup_dir"
    
    # Backup current state
    if docker-compose -f /opt/autotrainx/docker-compose.yml ps -q api > /dev/null 2>&1; then
        # Backup database
        docker-compose -f /opt/autotrainx/docker-compose.yml exec -T api \
            sqlite3 /app/DB/executions.db ".backup /tmp/pre_deploy_backup.db" || true
        docker cp autotrainx-api:/tmp/pre_deploy_backup.db "$backup_dir/${backup_name}.db" || true
        
        # Backup configuration
        cp /opt/autotrainx/.env "$backup_dir/${backup_name}.env" || true
        
        log_success "Backup created: $backup_name"
        echo "$backup_name" > /tmp/autotrainx_last_backup
    else
        log_warning "No running containers found, skipping backup"
    fi
}

deploy_application() {
    log_info "Deploying AutoTrainX API..."
    
    cd /opt/autotrainx
    
    # Update environment variables
    export VERSION="$VERSION"
    export BUILD_DATE="$BUILD_DATE"
    export VCS_REF="$VCS_REF"
    
    # Pull latest configuration
    if [[ -d "$PROJECT_ROOT" ]]; then
        cp "$PROJECT_ROOT/docker-compose.yml" /opt/autotrainx/
        cp "$PROJECT_ROOT/.env.example" /opt/autotrainx/ || true
    fi
    
    # Stop current services
    log_info "Stopping current services..."
    docker-compose down || true
    
    # Start new services
    log_info "Starting updated services..."
    if ! docker-compose up -d; then
        log_error "Failed to start services"
        return 1
    fi
    
    # Wait for services to be ready
    log_info "Waiting for services to be ready..."
    local max_attempts=30
    local attempt=0
    
    while [[ $attempt -lt $max_attempts ]]; do
        if curl -f -s http://localhost:8000/health > /dev/null 2>&1; then
            log_success "Services are ready"
            return 0
        fi
        
        log_info "Waiting for services... ($((attempt + 1))/$max_attempts)"
        sleep 10
        ((attempt++))
    done
    
    log_error "Services failed to become ready within timeout"
    return 1
}

health_check() {
    log_info "Performing health check..."
    
    local health_url="http://localhost:8000/health"
    local max_attempts=5
    local attempt=0
    
    while [[ $attempt -lt $max_attempts ]]; do
        if response=$(curl -f -s "$health_url" 2>/dev/null); then
            if echo "$response" | grep -q '"status":"healthy"'; then
                log_success "Health check passed"
                return 0
            fi
        fi
        
        log_warning "Health check attempt $((attempt + 1))/$max_attempts failed"
        sleep 5
        ((attempt++))
    done
    
    log_error "Health check failed after $max_attempts attempts"
    return 1
}

rollback_deployment() {
    if [[ "$ROLLBACK_ON_FAILURE" != "true" ]]; then
        log_warning "Rollback disabled, manual intervention required"
        return 1
    fi
    
    log_warning "Rolling back deployment..."
    
    # Get last backup name
    if [[ -f /tmp/autotrainx_last_backup ]]; then
        local backup_name=$(cat /tmp/autotrainx_last_backup)
        local backup_dir="/opt/autotrainx/backups/pre-deploy"
        
        if [[ -f "$backup_dir/${backup_name}.db" ]]; then
            log_info "Restoring database from backup..."
            docker cp "$backup_dir/${backup_name}.db" autotrainx-api:/tmp/restore.db
            docker-compose -f /opt/autotrainx/docker-compose.yml exec -T api \
                sqlite3 /app/DB/executions.db ".restore /tmp/restore.db"
        fi
        
        if [[ -f "$backup_dir/${backup_name}.env" ]]; then
            log_info "Restoring configuration from backup..."
            cp "$backup_dir/${backup_name}.env" /opt/autotrainx/.env
        fi
    fi
    
    # Restart services with previous configuration
    docker-compose -f /opt/autotrainx/docker-compose.yml restart
    
    log_warning "Rollback completed. Please check logs and fix issues."
}

cleanup() {
    log_info "Cleaning up..."
    
    # Remove old images (keep last 3 versions)
    docker images autotrainx-api --format "{{.Tag}}" | \
        grep -v latest | sort -V | head -n -3 | \
        xargs -r -I {} docker rmi autotrainx-api:{} || true
    
    # Clean build cache
    docker builder prune -f || true
    
    log_success "Cleanup completed"
}

main() {
    log_info "Starting AutoTrainX deployment..."
    log_info "Version: $VERSION"
    log_info "Environment: $DEPLOY_ENV"
    log_info "Build Date: $BUILD_DATE"
    
    parse_args "$@"
    check_prerequisites
    
    # Build phase
    if [[ "${DEPLOY_ONLY:-false}" != "true" ]]; then
        run_tests
        build_images
        push_images
    fi
    
    # Deploy phase
    if [[ "${BUILD_ONLY:-false}" != "true" ]]; then
        backup_current_state
        
        if deploy_application && health_check; then
            log_success "Deployment completed successfully!"
            cleanup
        else
            log_error "Deployment failed!"
            rollback_deployment
            exit 1
        fi
    fi
    
    log_success "AutoTrainX deployment process completed!"
}

# Handle script interruption
trap 'log_error "Deployment interrupted"; exit 1' INT TERM

# Run main function
main "$@"