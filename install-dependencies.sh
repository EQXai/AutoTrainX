#!/bin/bash

# AutoTrainX Dependencies Installation Script
# For Ubuntu/Debian/WSL2 systems

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Function to print colored output
print_color() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Function to print headers
print_header() {
    echo ""
    print_color "$BLUE" "=========================================="
    print_color "$BLUE" "$1"
    print_color "$BLUE" "=========================================="
    echo ""
}

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$NAME
    VER=$VERSION_ID
else
    print_color "$RED" "Cannot detect OS version"
    exit 1
fi

print_header "Installing Dependencies for AutoTrainX Web"
print_color "$GREEN" "Detected OS: $OS $VER"

# Update package list
print_color "$BLUE" "Updating package list..."
sudo apt-get update

# Install prerequisites
print_color "$BLUE" "Installing prerequisites..."
sudo apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    software-properties-common

# Install Docker
print_header "Installing Docker"

# Remove old versions
print_color "$BLUE" "Removing old Docker versions if any..."
sudo apt-get remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true

# Add Docker's official GPG key
print_color "$BLUE" "Adding Docker GPG key..."
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Add Docker repository
print_color "$BLUE" "Adding Docker repository..."
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Update package list again
sudo apt-get update

# Install Docker
print_color "$BLUE" "Installing Docker Engine..."
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Install Docker Compose standalone (for compatibility)
print_header "Installing Docker Compose"

print_color "$BLUE" "Installing Docker Compose v2..."
DOCKER_COMPOSE_VERSION="v2.24.0"
sudo curl -L "https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Add current user to docker group
print_header "Configuring Docker Permissions"

print_color "$BLUE" "Adding user to docker group..."
sudo usermod -aG docker $USER

# Configure Docker for WSL2 if applicable
if grep -qi microsoft /proc/version; then
    print_header "Configuring Docker for WSL2"
    
    # Create docker config directory
    mkdir -p ~/.docker
    
    # Configure Docker daemon for WSL2
    print_color "$BLUE" "Configuring Docker daemon for WSL2..."
    sudo tee /etc/docker/daemon.json > /dev/null <<EOF
{
    "hosts": ["unix:///var/run/docker.sock"],
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "10m",
        "max-file": "3"
    },
    "storage-driver": "overlay2"
}
EOF
    
    # Start Docker service
    print_color "$BLUE" "Starting Docker service..."
    sudo service docker start || true
    
    # Enable Docker to start on boot (systemd)
    if command -v systemctl >/dev/null 2>&1; then
        sudo systemctl enable docker || true
    fi
fi

# Install additional useful tools
print_header "Installing Additional Tools"

print_color "$BLUE" "Installing useful tools..."
sudo apt-get install -y \
    git \
    wget \
    htop \
    ncdu \
    tree \
    jq \
    make

# Verify installations
print_header "Verifying Installations"

# Check Docker
if command -v docker >/dev/null 2>&1; then
    DOCKER_VERSION=$(docker --version)
    print_color "$GREEN" "✓ Docker installed: $DOCKER_VERSION"
else
    print_color "$RED" "✗ Docker installation failed"
fi

# Check Docker Compose
if docker compose version >/dev/null 2>&1; then
    COMPOSE_VERSION=$(docker compose version)
    print_color "$GREEN" "✓ Docker Compose v2 installed: $COMPOSE_VERSION"
else
    print_color "$YELLOW" "⚠ Docker Compose v2 not available"
fi

if command -v docker-compose >/dev/null 2>&1; then
    COMPOSE_STANDALONE_VERSION=$(docker-compose --version)
    print_color "$GREEN" "✓ Docker Compose standalone installed: $COMPOSE_STANDALONE_VERSION"
else
    print_color "$YELLOW" "⚠ Docker Compose standalone not available"
fi

# Check if Docker service is running
if sudo docker ps >/dev/null 2>&1; then
    print_color "$GREEN" "✓ Docker daemon is running"
else
    print_color "$YELLOW" "⚠ Docker daemon is not running"
    print_color "$YELLOW" "  Try: sudo service docker start"
fi

# WSL2 specific instructions
if grep -qi microsoft /proc/version; then
    print_header "WSL2 Additional Steps"
    
    print_color "$YELLOW" "For WSL2, you may need to:"
    print_color "$YELLOW" "1. Restart your WSL2 session for group changes to take effect"
    print_color "$YELLOW" "2. If Docker doesn't start automatically, run: sudo service docker start"
    print_color "$YELLOW" "3. For GPU support, install NVIDIA Docker runtime in Windows Docker Desktop"
    echo ""
    print_color "$BLUE" "To restart WSL2, run in PowerShell:"
    print_color "$BLUE" "  wsl --shutdown"
    print_color "$BLUE" "  wsl"
fi

print_header "Installation Complete"

print_color "$GREEN" "✅ All dependencies have been installed!"
print_color "$YELLOW" ""
print_color "$YELLOW" "IMPORTANT: You need to log out and log back in for the docker group changes to take effect."
print_color "$YELLOW" "Alternatively, run: newgrp docker"
print_color "$YELLOW" ""
print_color "$BLUE" "After re-login, you can run:"
print_color "$BLUE" "  ./manage-web.sh install"
print_color "$BLUE" ""
print_color "$BLUE" "To test Docker without sudo, run:"
print_color "$BLUE" "  docker run hello-world"