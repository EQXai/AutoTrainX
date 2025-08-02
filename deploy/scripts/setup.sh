#!/bin/bash

# AutoTrainX Production Deployment Setup Script
# This script prepares the environment for production deployment

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DEPLOY_ENV="${DEPLOY_ENV:-production}"
DOCKER_REGISTRY="${DOCKER_REGISTRY:-}"
SSL_EMAIL="${SSL_EMAIL:-admin@example.com}"
DOMAIN="${DOMAIN:-autotrainx.example.com}"
BACKUP_ENABLED="${BACKUP_ENABLED:-true}"

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if running as root or with sudo
    if [[ $EUID -eq 0 ]]; then
        log_warning "Running as root. Consider using a non-root user with sudo."
    fi
    
    # Check required commands
    local required_commands=("docker" "docker-compose" "curl" "openssl")
    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            log_error "Required command '$cmd' not found. Please install it first."
            exit 1
        fi
    done
    
    # Check Docker daemon
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running or accessible."
        exit 1
    fi
    
    log_success "Prerequisites check completed"
}

setup_directories() {
    log_info "Setting up directory structure..."
    
    # Create necessary directories
    local directories=(
        "/opt/autotrainx"
        "/opt/autotrainx/data"
        "/opt/autotrainx/backups"
        "/opt/autotrainx/ssl"
        "/opt/autotrainx/logs"
        "/var/log/autotrainx"
    )
    
    for dir in "${directories[@]}"; do
        if [[ ! -d "$dir" ]]; then
            sudo mkdir -p "$dir"
            log_info "Created directory: $dir"
        fi
    done
    
    # Set proper permissions
    sudo chown -R $USER:$USER /opt/autotrainx
    sudo chmod -R 755 /opt/autotrainx
    
    log_success "Directory structure setup completed"
}

generate_ssl_certificates() {
    log_info "Generating SSL certificates..."
    
    local ssl_dir="/opt/autotrainx/ssl"
    local cert_file="$ssl_dir/cert.pem"
    local key_file="$ssl_dir/key.pem"
    
    if [[ ! -f "$cert_file" || ! -f "$key_file" ]]; then
        log_info "Generating self-signed SSL certificate for development..."
        
        openssl req -x509 -newkey rsa:4096 -keyout "$key_file" -out "$cert_file" \
            -days 365 -nodes -subj "/C=US/ST=State/L=City/O=Organization/CN=$DOMAIN"
        
        chmod 600 "$key_file"
        chmod 644 "$cert_file"
        
        log_success "SSL certificates generated"
        log_warning "Using self-signed certificates. For production, use Let's Encrypt or proper CA certificates."
    else
        log_info "SSL certificates already exist"
    fi
}

setup_environment() {
    log_info "Setting up environment configuration..."
    
    local env_file="/opt/autotrainx/.env"
    
    if [[ ! -f "$env_file" ]]; then
        log_info "Creating environment file from template..."
        
        # Copy template and customize
        cp "$PROJECT_ROOT/.env.example" "$env_file"
        
        # Generate secure secret key
        local secret_key=$(openssl rand -hex 32)
        sed -i "s/your-very-secure-secret-key-change-this-in-production/$secret_key/" "$env_file"
        
        # Set domain
        sed -i "s/autotrainx.example.com/$DOMAIN/" "$env_file"
        
        # Set environment
        sed -i "s/ENVIRONMENT=production/ENVIRONMENT=$DEPLOY_ENV/" "$env_file"
        
        # Set SSL paths
        sed -i "s|/etc/nginx/ssl/cert.pem|/opt/autotrainx/ssl/cert.pem|" "$env_file"
        sed -i "s|/etc/nginx/ssl/key.pem|/opt/autotrainx/ssl/key.pem|" "$env_file"
        
        chmod 600 "$env_file"
        log_success "Environment file created"
    else
        log_info "Environment file already exists"
    fi
}

setup_docker_network() {
    log_info "Setting up Docker networks..."
    
    # Create custom network if it doesn't exist
    if ! docker network ls | grep -q "autotrainx-network"; then
        docker network create autotrainx-network --driver bridge --subnet=172.20.0.0/16
        log_success "Docker network created"
    else
        log_info "Docker network already exists"
    fi
}

setup_systemd_service() {
    log_info "Setting up systemd service..."
    
    local service_file="/etc/systemd/system/autotrainx.service"
    
    if [[ ! -f "$service_file" ]]; then
        sudo tee "$service_file" > /dev/null << EOF
[Unit]
Description=AutoTrainX API Service
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
User=$USER
Group=$USER
WorkingDirectory=/opt/autotrainx
ExecStart=/usr/local/bin/docker-compose -f /opt/autotrainx/docker-compose.yml up -d
ExecStop=/usr/local/bin/docker-compose -f /opt/autotrainx/docker-compose.yml down
TimeoutStartSec=300
TimeoutStopSec=60

[Install]
WantedBy=multi-user.target
EOF
        
        sudo systemctl daemon-reload
        sudo systemctl enable autotrainx.service
        
        log_success "Systemd service created and enabled"
    else
        log_info "Systemd service already exists"
    fi
}

setup_logrotate() {
    log_info "Setting up log rotation..."
    
    local logrotate_file="/etc/logrotate.d/autotrainx"
    
    if [[ ! -f "$logrotate_file" ]]; then
        sudo tee "$logrotate_file" > /dev/null << EOF
/var/log/autotrainx/*.log
/opt/autotrainx/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 $USER $USER
    postrotate
        docker-compose -f /opt/autotrainx/docker-compose.yml exec api pkill -USR1 -f uvicorn || true
    endscript
}
EOF
        
        log_success "Log rotation configured"
    else
        log_info "Log rotation already configured"
    fi
}

setup_backup_script() {
    if [[ "$BACKUP_ENABLED" != "true" ]]; then
        log_info "Backup disabled, skipping backup setup"
        return
    fi
    
    log_info "Setting up backup script..."
    
    local backup_script="/opt/autotrainx/backup.sh"
    
    cat > "$backup_script" << 'EOF'
#!/bin/bash

# AutoTrainX Backup Script
set -euo pipefail

BACKUP_DIR="/opt/autotrainx/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="autotrainx_backup_$TIMESTAMP"

# Create backup directory
mkdir -p "$BACKUP_DIR/$BACKUP_NAME"

# Backup database
docker-compose -f /opt/autotrainx/docker-compose.yml exec -T api \
    sqlite3 /app/DB/executions.db ".backup /tmp/backup.db"
docker cp autotrainx-api:/tmp/backup.db "$BACKUP_DIR/$BACKUP_NAME/executions.db"

# Backup configuration
cp -r /opt/autotrainx/.env "$BACKUP_DIR/$BACKUP_NAME/"
cp -r /opt/autotrainx/Presets "$BACKUP_DIR/$BACKUP_NAME/" 2>/dev/null || true

# Compress backup
cd "$BACKUP_DIR"
tar -czf "$BACKUP_NAME.tar.gz" "$BACKUP_NAME"
rm -rf "$BACKUP_NAME"

# Clean old backups (keep last 7 days)
find "$BACKUP_DIR" -name "autotrainx_backup_*.tar.gz" -mtime +7 -delete

echo "Backup completed: $BACKUP_NAME.tar.gz"
EOF
    
    chmod +x "$backup_script"
    
    # Setup cron job
    (crontab -l 2>/dev/null; echo "0 2 * * * /opt/autotrainx/backup.sh >> /var/log/autotrainx/backup.log 2>&1") | crontab -
    
    log_success "Backup script and cron job configured"
}

copy_deployment_files() {
    log_info "Copying deployment files..."
    
    # Copy Docker Compose files
    cp "$PROJECT_ROOT/docker-compose.yml" /opt/autotrainx/
    cp "$PROJECT_ROOT/Dockerfile" /opt/autotrainx/
    cp "$PROJECT_ROOT/.dockerignore" /opt/autotrainx/
    
    # Copy Nginx configuration
    mkdir -p /opt/autotrainx/nginx
    cp -r "$PROJECT_ROOT/deploy/nginx/"* /opt/autotrainx/nginx/
    
    # Copy monitoring configuration
    if [[ -d "$PROJECT_ROOT/deploy/monitoring" ]]; then
        cp -r "$PROJECT_ROOT/deploy/monitoring" /opt/autotrainx/
    fi
    
    log_success "Deployment files copied"
}

setup_firewall() {
    log_info "Configuring firewall..."
    
    if command -v ufw &> /dev/null; then
        # Allow SSH
        sudo ufw allow ssh
        
        # Allow HTTP and HTTPS
        sudo ufw allow 80/tcp
        sudo ufw allow 443/tcp
        
        # Allow monitoring ports (from local network only)
        sudo ufw allow from 192.168.0.0/16 to any port 3000
        sudo ufw allow from 192.168.0.0/16 to any port 9090
        
        # Enable firewall if not already enabled
        sudo ufw --force enable
        
        log_success "Firewall configured"
    else
        log_warning "UFW not found. Please configure firewall manually."
    fi
}

main() {
    log_info "Starting AutoTrainX production deployment setup..."
    
    check_prerequisites
    setup_directories
    generate_ssl_certificates
    setup_environment
    setup_docker_network
    copy_deployment_files
    setup_systemd_service
    setup_logrotate
    setup_backup_script
    setup_firewall
    
    log_success "AutoTrainX deployment setup completed!"
    
    echo
    log_info "Next steps:"
    echo "1. Review and customize /opt/autotrainx/.env"
    echo "2. Place your SSL certificates in /opt/autotrainx/ssl/"
    echo "3. Start the service: sudo systemctl start autotrainx"
    echo "4. Check status: sudo systemctl status autotrainx"
    echo "5. View logs: docker-compose -f /opt/autotrainx/docker-compose.yml logs -f"
    echo
}

# Run main function
main "$@"