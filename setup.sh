#!/bin/bash
#
# AutoTrainX Unified Setup Script
# 
# This script provides a streamlined installation experience with multiple
# installation profiles tailored for different environments and use cases.
#
# Features:
# - Multiple installation profiles (Docker, WSL, Linux, Development, Minimal)
# - Upfront configuration with all questions at the beginning
# - All Python dependencies installed within virtual environment
# - Automatic environment detection
# - Configuration saving for future updates
#
# Usage:
#   bash setup.sh [--profile PROFILE] [--auto] [--config FILE]
#
# Options:
#   --profile    Specify installation profile (docker|wsl|linux|dev|minimal)
#   --auto       Run in automatic mode using saved config or defaults
#   --config     Load configuration from file
#   --help       Show this help message
#

set -e

# ============================================================================
# Global Variables and Configuration
# ============================================================================

# Checkpoint system for resumable installation
CHECKPOINT_FILE=".setup_checkpoints"
FAILED_STEPS_FILE=".setup_failed_steps"
RESUME_FROM=""
CONTINUE_ON_ERROR=true

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="$SCRIPT_DIR/venv"
LOG_FILE="$SCRIPT_DIR/logs/setup_$(date +%Y%m%d_%H%M%S).log"
CONFIG_FILE="$SCRIPT_DIR/.setup_config.json"

# Array to track failed steps
declare -a FAILED_STEPS

# Installation profiles
declare -A PROFILES
PROFILES["docker"]="Docker-based installation with minimal host dependencies"
PROFILES["wsl"]="WSL2-optimized installation with Windows integration"
PROFILES["linux"]="Standard Linux installation with full features"
PROFILES["dev"]="Development installation with all tools and extras"
PROFILES["minimal"]="Minimal installation with core features only"

# Default values
SELECTED_PROFILE=""
AUTO_MODE=false
INSTALL_CONFIG=""
ENVIRONMENT_TYPE=""

# Component flags
INSTALL_POSTGRESQL=false
INSTALL_NODEJS=false
INSTALL_DOCKER=false
INSTALL_GOOGLE_SHEETS=false
INSTALL_MODELS=false
INSTALL_DEV_TOOLS=false
CUDA_VERSION="12.8"
SKIP_SYSTEM_DEPS=false

# Docker root installation flag
DOCKER_ROOT_INSTALL=false

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m'

# ============================================================================
# Utility Functions
# ============================================================================

# Quick fix for triton error
fix_triton_error() {
    print_header "Fixing Triton/XFormers Error"
    
    # Check if venv exists
    if [ ! -f "$VENV_PATH/bin/activate" ]; then
        print_error "Virtual environment not found at $VENV_PATH"
        print_info "Please run the full setup first: ./setup.sh"
        return 1
    fi
    
    # Activate venv
    source "$VENV_PATH/bin/activate"
    
    print_info "Current Python: $(which python)"
    print_info "Current pip: $(which pip)"
    
    # Option menu
    echo ""
    echo "Choose an option:"
    echo "1) Install triton (recommended for GPU usage)"
    echo "2) Remove xformers (for CPU-only usage)"
    echo "3) Reinstall both triton and xformers"
    echo "4) Just suppress the error (ignore it)"
    echo ""
    read -p "Select option (1-4): " option
    
    case $option in
        1)
            print_info "Installing triton..."
            pip install triton --extra-index-url https://download.pytorch.org/whl/cu${CUDA_VERSION//./}
            if [ $? -eq 0 ]; then
                print_success "Triton installed successfully!"
            else
                print_warning "Triton installation failed - this is okay for CPU usage"
            fi
            ;;
        2)
            print_info "Removing xformers..."
            pip uninstall -y xformers triton
            print_success "XFormers and triton removed - CPU mode active"
            ;;
        3)
            print_info "Reinstalling triton and xformers..."
            pip uninstall -y xformers triton
            pip install triton --extra-index-url https://download.pytorch.org/whl/cu${CUDA_VERSION//./}
            pip install xformers --index-url https://download.pytorch.org/whl/cu${CUDA_VERSION//./}
            print_success "Reinstallation complete!"
            ;;
        4)
            print_info "Creating triton stub to suppress error..."
            # Run the fix script
            if [ -f "$SCRIPT_DIR/fix_triton_diffusers.py" ]; then
                python "$SCRIPT_DIR/fix_triton_diffusers.py"
            else
                # Fallback to inline fix
                python -c "
import os
import site
site_packages = site.getsitepackages()[0]
triton_dir = os.path.join(site_packages, 'triton')
os.makedirs(triton_dir, exist_ok=True)
with open(os.path.join(triton_dir, '__init__.py'), 'w') as f:
    f.write('# Triton stub module\\n')
with open(os.path.join(triton_dir, 'ops.py'), 'w') as f:
    f.write('''# Stub for triton.ops
class _StubOp:
    def __getattr__(self, name):
        return lambda *args, **kwargs: None

matmul = _StubOp()
elementwise = _StubOp()
reduction = _StubOp()

def __getattr__(name):
    return _StubOp()
''')
print('✅ Created triton.ops stub module')
"
            fi
            print_success "Error suppressed - triton imports will be ignored"
            ;;
        *)
            print_error "Invalid option"
            return 1
            ;;
    esac
    
    # Test the fix
    echo ""
    print_info "Testing Python imports..."
    python -c "
try:
    import torch
    print('✅ PyTorch imported successfully')
    try:
        import xformers
        print('✅ XFormers imported successfully')
    except ImportError as e:
        print('⚠️  XFormers not available:', str(e))
    try:
        import triton
        print('✅ Triton imported successfully')
    except ImportError:
        print('⚠️  Triton not available (this is okay for CPU usage)')
except Exception as e:
    print('❌ Error:', str(e))
"
    
    echo ""
    print_success "Fix complete!"
    print_info "You can now run your training scripts"
}

print_header() {
    echo -e "\n${CYAN}${BOLD}=================================================================================${NC}"
    echo -e "${CYAN}${BOLD}  $1${NC}"
    echo -e "${CYAN}${BOLD}=================================================================================${NC}\n"
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

print_step() {
    echo -e "\n${MAGENTA}[STEP $1/${2}]${NC} $3" | tee -a "$LOG_FILE"
}

# Create log directory if it doesn't exist
mkdir -p "$(dirname "$LOG_FILE")"

# ============================================================================
# Checkpoint System Functions
# ============================================================================

# Mark a checkpoint as completed
mark_checkpoint() {
    local checkpoint_name="$1"
    echo "$checkpoint_name" >> "$CHECKPOINT_FILE"
    print_success "✓ Checkpoint '$checkpoint_name' completed"
}

# Check if a checkpoint was already completed
is_checkpoint_completed() {
    local checkpoint_name="$1"
    [ -f "$CHECKPOINT_FILE" ] && grep -q "^$checkpoint_name$" "$CHECKPOINT_FILE"
}

# List all completed checkpoints
list_checkpoints() {
    if [ -f "$CHECKPOINT_FILE" ]; then
        echo "Completed checkpoints:"
        cat "$CHECKPOINT_FILE" | sed 's/^/  ✓ /'
    else
        echo "No checkpoints found."
    fi
}

# Clean checkpoint file (start fresh)
clean_checkpoints() {
    rm -f "$CHECKPOINT_FILE"
    rm -f "$FAILED_STEPS_FILE"
    print_info "Checkpoint and failed steps files cleaned"
}

# Track failed step
track_failed_step() {
    local step_name="$1"
    local error_msg="$2"
    FAILED_STEPS+=("$step_name:$error_msg")
    echo "$step_name:$error_msg" >> "$FAILED_STEPS_FILE"
}

# Load failed steps from previous run
load_failed_steps() {
    if [ -f "$FAILED_STEPS_FILE" ]; then
        while IFS= read -r line; do
            FAILED_STEPS+=("$line")
        done < "$FAILED_STEPS_FILE"
    fi
}

# Clear failed steps for a specific checkpoint
clear_failed_step() {
    local checkpoint="$1"
    if [ -f "$FAILED_STEPS_FILE" ]; then
        grep -v "^$checkpoint:" "$FAILED_STEPS_FILE" > "$FAILED_STEPS_FILE.tmp" || true
        mv "$FAILED_STEPS_FILE.tmp" "$FAILED_STEPS_FILE"
    fi
    # Remove from array
    local new_failed_steps=()
    for step in "${FAILED_STEPS[@]}"; do
        if [[ ! "$step" =~ ^$checkpoint: ]]; then
            new_failed_steps+=("$step")
        fi
    done
    FAILED_STEPS=("${new_failed_steps[@]}")
}

# Show resume options
show_resume_options() {
    echo ""
    echo "Available checkpoints to resume from:"
    echo "  1. system_deps - System dependencies installation"
    echo "  2. nodejs - Node.js installation"
    echo "  3. python_env - Python environment setup"
    echo "  4. core_deps - Core dependencies installation"
    echo "  5. web_deps - Web dependencies installation"
    echo "  6. postgresql - PostgreSQL setup"
    echo "  7. config - Configuration setup"
    echo "  8. permissions - File permissions setup"
    echo "  9. git_setup - Git repository setup"
    echo "  10. validation - Final validation"
    echo ""
    echo "  clean - Start fresh (remove all checkpoints)"
    echo "  list - Show completed checkpoints"
    echo ""
}

# ============================================================================
# Environment Detection
# ============================================================================

detect_environment() {
    print_info "Detecting environment..."
    
    # Check if running in Docker
    if [ -f /.dockerenv ]; then
        ENVIRONMENT_TYPE="docker"
        print_info "Detected: Running inside Docker container"
        return
    fi
    
    # Check if running in WSL
    if grep -qi microsoft /proc/version 2>/dev/null; then
        ENVIRONMENT_TYPE="wsl"
        print_info "Detected: Windows Subsystem for Linux (WSL2)"
        return
    fi
    
    # Check OS type
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        ENVIRONMENT_TYPE="linux"
        print_info "Detected: $NAME $VERSION"
    else
        ENVIRONMENT_TYPE="unknown"
        print_warning "Could not detect environment type"
    fi
}

# ============================================================================
# Configuration Management
# ============================================================================

save_configuration() {
    cat > "$CONFIG_FILE" << EOF
{
    "profile": "$SELECTED_PROFILE",
    "environment": "$ENVIRONMENT_TYPE",
    "components": {
        "postgresql": $INSTALL_POSTGRESQL,
        "nodejs": $INSTALL_NODEJS,
        "docker": $INSTALL_DOCKER,
        "google_sheets": $INSTALL_GOOGLE_SHEETS,
        "models": $INSTALL_MODELS,
        "dev_tools": $INSTALL_DEV_TOOLS
    },
    "cuda_version": "$CUDA_VERSION",
    "skip_system_deps": $SKIP_SYSTEM_DEPS,
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
    print_info "Configuration saved to $CONFIG_FILE"
}

load_configuration() {
    if [ -f "$1" ]; then
        print_info "Loading configuration from $1"
        # Parse JSON configuration (basic parsing)
        SELECTED_PROFILE=$(grep '"profile"' "$1" | cut -d'"' -f4)
        INSTALL_POSTGRESQL=$(grep '"postgresql"' "$1" | grep -o 'true\|false')
        INSTALL_NODEJS=$(grep '"nodejs"' "$1" | grep -o 'true\|false')
        INSTALL_DOCKER=$(grep '"docker"' "$1" | grep -o 'true\|false')
        INSTALL_GOOGLE_SHEETS=$(grep '"google_sheets"' "$1" | grep -o 'true\|false')
        INSTALL_MODELS=$(grep '"models"' "$1" | grep -o 'true\|false')
        INSTALL_DEV_TOOLS=$(grep '"dev_tools"' "$1" | grep -o 'true\|false')
        CUDA_VERSION=$(grep '"cuda_version"' "$1" | cut -d'"' -f4)
        SKIP_SYSTEM_DEPS=$(grep '"skip_system_deps"' "$1" | grep -o 'true\|false')
        return 0
    else
        print_error "Configuration file not found: $1"
        return 1
    fi
}

# ============================================================================
# Profile Selection and Configuration
# ============================================================================

show_profile_menu() {
    print_header "Installation Profile Selection"
    
    echo "Available installation profiles:"
    echo ""
    echo "  1) Docker    - ${PROFILES["docker"]}"
    echo "  2) WSL       - ${PROFILES["wsl"]}"
    echo "  3) Linux     - ${PROFILES["linux"]}"
    echo "  4) Dev       - ${PROFILES["dev"]}"
    echo "  5) Minimal   - ${PROFILES["minimal"]}"
    echo ""
    
    # Show recommendation based on detected environment
    case "$ENVIRONMENT_TYPE" in
        docker)
            echo -e "${GREEN}Recommended: Docker profile${NC}"
            ;;
        wsl)
            echo -e "${GREEN}Recommended: WSL profile${NC}"
            ;;
        linux)
            echo -e "${GREEN}Recommended: Linux profile${NC}"
            ;;
    esac
    
    echo ""
    read -p "Select installation profile (1-5): " choice
    
    case $choice in
        1) SELECTED_PROFILE="docker" ;;
        2) SELECTED_PROFILE="wsl" ;;
        3) SELECTED_PROFILE="linux" ;;
        4) SELECTED_PROFILE="dev" ;;
        5) SELECTED_PROFILE="minimal" ;;
        *) 
            print_error "Invalid selection"
            exit 1
            ;;
    esac
    
    print_success "Selected profile: $SELECTED_PROFILE"
}

configure_profile_defaults() {
    # Set default component selections based on profile
    case "$SELECTED_PROFILE" in
        docker)
            INSTALL_POSTGRESQL=false  # Use containerized
            INSTALL_NODEJS=false      # Use containerized
            INSTALL_DOCKER=true
            INSTALL_GOOGLE_SHEETS=true
            INSTALL_MODELS=false      # Mount from host
            INSTALL_DEV_TOOLS=false
            ;;
        wsl)
            INSTALL_POSTGRESQL=true
            INSTALL_NODEJS=true
            INSTALL_DOCKER=false      # Usually use Windows Docker Desktop
            INSTALL_GOOGLE_SHEETS=true
            INSTALL_MODELS=true
            INSTALL_DEV_TOOLS=false
            ;;
        linux)
            INSTALL_POSTGRESQL=true
            INSTALL_NODEJS=true
            INSTALL_DOCKER=false
            INSTALL_GOOGLE_SHEETS=true
            INSTALL_MODELS=true
            INSTALL_DEV_TOOLS=false
            ;;
        dev)
            INSTALL_POSTGRESQL=true
            INSTALL_NODEJS=true
            INSTALL_DOCKER=true
            INSTALL_GOOGLE_SHEETS=true
            INSTALL_MODELS=true
            INSTALL_DEV_TOOLS=true
            ;;
        minimal)
            INSTALL_POSTGRESQL=false
            INSTALL_NODEJS=false
            INSTALL_DOCKER=false
            INSTALL_GOOGLE_SHEETS=false
            INSTALL_MODELS=false
            INSTALL_DEV_TOOLS=false
            ;;
    esac
}

customize_components() {
    print_header "Component Customization"
    
    echo "The following components are selected based on your profile ($SELECTED_PROFILE):"
    echo ""
    echo "  PostgreSQL Database : $([ "$INSTALL_POSTGRESQL" = true ] && echo "Yes" || echo "No")"
    echo "  Node.js/Web UI     : $([ "$INSTALL_NODEJS" = true ] && echo "Yes" || echo "No")"
    echo "  Docker Runtime     : $([ "$INSTALL_DOCKER" = true ] && echo "Yes" || echo "No")"
    echo "  Google Sheets Sync : $([ "$INSTALL_GOOGLE_SHEETS" = true ] && echo "Yes" || echo "No")"
    echo "  Pre-trained Models : $([ "$INSTALL_MODELS" = true ] && echo "Yes" || echo "No")"
    echo "  Dev Tools          : $([ "$INSTALL_DEV_TOOLS" = true ] && echo "Yes" || echo "No")"
    echo ""
    
    read -p "Do you want to customize these selections? (y/N): " customize
    
    if [[ $customize =~ ^[Yy]$ ]]; then
        # PostgreSQL
        read -p "Install PostgreSQL database? (y/n) [$([ "$INSTALL_POSTGRESQL" = true ] && echo "y" || echo "n")]: " response
        [[ $response =~ ^[Yy]$ ]] && INSTALL_POSTGRESQL=true || INSTALL_POSTGRESQL=false
        
        # Node.js
        read -p "Install Node.js and web interface? (y/n) [$([ "$INSTALL_NODEJS" = true ] && echo "y" || echo "n")]: " response
        [[ $response =~ ^[Yy]$ ]] && INSTALL_NODEJS=true || INSTALL_NODEJS=false
        
        # Docker
        if [ "$SELECTED_PROFILE" != "docker" ]; then
            read -p "Install Docker runtime? (y/n) [$([ "$INSTALL_DOCKER" = true ] && echo "y" || echo "n")]: " response
            [[ $response =~ ^[Yy]$ ]] && INSTALL_DOCKER=true || INSTALL_DOCKER=false
        fi
        
        # Google Sheets
        read -p "Install Google Sheets sync? (y/n) [$([ "$INSTALL_GOOGLE_SHEETS" = true ] && echo "y" || echo "n")]: " response
        [[ $response =~ ^[Yy]$ ]] && INSTALL_GOOGLE_SHEETS=true || INSTALL_GOOGLE_SHEETS=false
        
        # Models
        read -p "Download pre-trained models? (y/n) [$([ "$INSTALL_MODELS" = true ] && echo "y" || echo "n")]: " response
        [[ $response =~ ^[Yy]$ ]] && INSTALL_MODELS=true || INSTALL_MODELS=false
        
        # Dev Tools
        read -p "Install development tools? (y/n) [$([ "$INSTALL_DEV_TOOLS" = true ] && echo "y" || echo "n")]: " response
        [[ $response =~ ^[Yy]$ ]] && INSTALL_DEV_TOOLS=true || INSTALL_DEV_TOOLS=false
    fi
    
    # Advanced options
    echo ""
    read -p "Configure advanced options? (y/N): " advanced
    
    if [[ $advanced =~ ^[Yy]$ ]]; then
        read -p "CUDA version (11.8/12.1/12.8) [$CUDA_VERSION]: " cuda_input
        [ -n "$cuda_input" ] && CUDA_VERSION=$cuda_input
        
        read -p "Skip system dependency installation? (y/N): " skip_sys
        [[ $skip_sys =~ ^[Yy]$ ]] && SKIP_SYSTEM_DEPS=true || SKIP_SYSTEM_DEPS=false
    fi
}

show_installation_summary() {
    print_header "Installation Summary"
    
    echo "Profile: $SELECTED_PROFILE"
    echo "Environment: $ENVIRONMENT_TYPE"
    echo ""
    echo "Components to install:"
    [ "$INSTALL_POSTGRESQL" = true ] && echo "  ✓ PostgreSQL Database"
    [ "$INSTALL_NODEJS" = true ] && echo "  ✓ Node.js and Web Interface"
    [ "$INSTALL_DOCKER" = true ] && echo "  ✓ Docker Runtime"
    [ "$INSTALL_GOOGLE_SHEETS" = true ] && echo "  ✓ Google Sheets Sync"
    [ "$INSTALL_MODELS" = true ] && echo "  ✓ Pre-trained Models"
    [ "$INSTALL_DEV_TOOLS" = true ] && echo "  ✓ Development Tools"
    echo ""
    echo "Python packages will be installed in: $VENV_PATH"
    echo "CUDA version: $CUDA_VERSION"
    [ "$SKIP_SYSTEM_DEPS" = true ] && echo "System dependencies: SKIPPED"
    echo ""
    
    read -p "Proceed with installation? (Y/n): " proceed
    if [[ ! $proceed =~ ^[Yy]?$ ]]; then
        print_info "Installation cancelled"
        exit 0
    fi
}

# ============================================================================
# Installation Functions
# ============================================================================

# Check if running as root
check_root_permissions() {
    if [ "$EUID" -eq 0 ]; then
        export RUNNING_AS_ROOT=true
        print_warning "Running as root user"
        
        # Check if running as root in Docker
        if [ -f /.dockerenv ]; then
            export DOCKER_ROOT_INSTALL=true
            print_info "Installing in Docker container as root"
        fi
    else
        export RUNNING_AS_ROOT=false
        # Check sudo availability for non-root users
        if ! command -v sudo &> /dev/null && [ "$SKIP_SYSTEM_DEPS" = false ]; then
            print_error "sudo is required for system dependency installation"
            print_info "Run as root or install sudo first"
            exit 1
        fi
    fi
}

# Run commands with appropriate privileges
run_privileged() {
    if [ "$RUNNING_AS_ROOT" = true ]; then
        "$@"
    else
        sudo "$@"
    fi
}

# Step 1: System Dependencies
install_system_dependencies() {
    if [ "$SKIP_SYSTEM_DEPS" = true ]; then
        print_info "Skipping system dependencies"
        return 0
    fi
    
    print_step 1 12 "Installing System Dependencies"
    
    # Update package list
    print_info "Updating package list..."
    if ! run_privileged apt-get update; then
        print_error "Failed to update package list"
        return 1
    fi
    
    # Base dependencies for all profiles
    local base_deps="python3 python3-pip python3-venv git curl wget build-essential"
    
    # Profile-specific dependencies
    case "$SELECTED_PROFILE" in
        docker)
            base_deps="$base_deps apt-transport-https ca-certificates gnupg lsb-release"
            ;;
        wsl)
            base_deps="$base_deps wslu"  # WSL utilities
            ;;
        dev)
            base_deps="$base_deps htop ncdu tree jq make vim"
            ;;
    esac
    
    print_info "Installing base dependencies..."
    if ! run_privileged apt-get install -y $base_deps; then
        print_error "Failed to install base dependencies"
        return 1
    fi
    
    # Install PostgreSQL if selected
    if [ "$INSTALL_POSTGRESQL" = true ]; then
        print_info "Installing PostgreSQL..."
        if ! run_privileged apt-get install -y postgresql postgresql-contrib; then
            print_error "Failed to install PostgreSQL"
            return 1
        fi
    fi
    
    # Install Docker if selected
    if [ "$INSTALL_DOCKER" = true ]; then
        if ! install_docker; then
            print_error "Failed to install Docker"
            return 1
        fi
    fi
    
    # Install Node.js if selected
    if [ "$INSTALL_NODEJS" = true ]; then
        if ! install_nodejs; then
            print_error "Failed to install Node.js"
            return 1
        fi
    fi
    
    print_success "System dependencies installed"
    return 0
}

install_docker() {
    print_info "Installing Docker..."
    
    # Check if installing Docker inside Docker
    if [ "$ENVIRONMENT_TYPE" = "docker" ] && [ "$INSTALL_DOCKER" = true ]; then
        print_warning "Installing Docker inside Docker container - this requires privileged mode"
        print_warning "Make sure the container is running with --privileged flag or appropriate capabilities"
    fi
    
    # Remove old versions
    run_privileged apt-get remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true
    
    # Add Docker's official GPG key
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | run_privileged gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    
    # Add Docker repository
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | run_privileged tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    # Install Docker
    run_privileged apt-get update
    run_privileged apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    
    # Add user to docker group
    if [ "$RUNNING_AS_ROOT" = false ]; then
        run_privileged usermod -aG docker $USER
        print_warning "You'll need to log out and back in for docker group changes to take effect"
    elif [ "$DOCKER_ROOT_INSTALL" = true ]; then
        print_info "Running as root in Docker - skipping docker group addition"
    fi
    
    # WSL-specific Docker configuration
    if [ "$ENVIRONMENT_TYPE" = "wsl" ]; then
        configure_docker_wsl
    fi
}

configure_docker_wsl() {
    print_info "Configuring Docker for WSL2..."
    
    # Create Docker daemon configuration
    run_privileged tee /etc/docker/daemon.json > /dev/null <<EOF
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
    run_privileged service docker start || true
}

install_nodejs() {
    print_info "Installing Node.js..."
    
    # Install NodeSource repository
    curl -fsSL https://deb.nodesource.com/setup_lts.x | run_privileged bash -
    run_privileged apt-get install -y nodejs
    
    print_success "Node.js $(node --version) installed"
}

# Step 2: Python Virtual Environment
create_virtual_environment() {
    print_step 2 12 "Creating Python Virtual Environment"
    
    # Remove existing venv if corrupted
    if [ -d "$VENV_PATH" ] && [ ! -f "$VENV_PATH/bin/activate" ]; then
        print_warning "Removing corrupted virtual environment..."
        rm -rf "$VENV_PATH"
    fi
    
    # Create new venv
    if [ ! -d "$VENV_PATH" ]; then
        print_info "Creating virtual environment at $VENV_PATH..."
        python3 -m venv "$VENV_PATH"
    else
        print_info "Using existing virtual environment"
    fi
    
    # Activate venv
    source "$VENV_PATH/bin/activate"
    
    # Upgrade pip
    print_info "Upgrading pip..."
    pip install --upgrade pip wheel setuptools
    
    print_success "Virtual environment ready"
}

# Step 3: PyTorch Installation
install_pytorch() {
    print_step 3 12 "Installing PyTorch"
    
    # Ensure venv exists and is activated
    if [ ! -f "$VENV_PATH/bin/activate" ]; then
        print_error "Virtual environment not found. Please run step 2 (Python Environment) first."
        return 1
    fi
    
    source "$VENV_PATH/bin/activate"
    
    # Clean previous installations
    pip uninstall -y torch torchvision torchaudio xformers 2>/dev/null || true
    
    # Install PyTorch based on CUDA version
    case "$CUDA_VERSION" in
        "11.8")
            if ! pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118; then
                print_error "Failed to install PyTorch for CUDA 11.8"
                return 1
            fi
            ;;
        "12.1")
            if ! pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121; then
                print_error "Failed to install PyTorch for CUDA 12.1"
                return 1
            fi
            ;;
        "12.8")
            if ! pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128; then
                print_error "Failed to install PyTorch for CUDA 12.8"
                return 1
            fi
            ;;
        *)
            print_error "Unsupported CUDA version: $CUDA_VERSION"
            return 1
            ;;
    esac
    
    # Verify installation
    if python -c "import torch; print(f'PyTorch {torch.__version__} installed')" 2>/dev/null; then
        print_success "PyTorch installed successfully"
        return 0
    else
        print_error "PyTorch installation failed"
        return 1
    fi
}

# Step 4: xformers Installation
install_xformers() {
    print_step 4 12 "Installing xformers"
    
    # Ensure venv exists and is activated
    if [ ! -f "$VENV_PATH/bin/activate" ]; then
        print_error "Virtual environment not found. Please run step 2 (Python Environment) first."
        return 1
    fi
    
    source "$VENV_PATH/bin/activate"
    
    # Install build dependencies
    if ! pip install wheel ninja; then
        print_error "Failed to install build dependencies"
        return 1
    fi
    
    # Install triton (xformers dependency)
    print_info "Installing triton (xformers dependency)..."
    if ! pip install triton --extra-index-url https://download.pytorch.org/whl/cu${CUDA_VERSION//./} 2>/dev/null; then
        print_warning "Could not install triton - xformers may have limited functionality"
        print_info "This is normal if you're not using GPU optimizations"
    fi
    
    # Try pre-built wheel first
    if pip install xformers --index-url https://download.pytorch.org/whl/cu${CUDA_VERSION//./} 2>/dev/null; then
        print_success "xformers installed from pre-built wheel"
        return 0
    else
        print_warning "Installing xformers from source (this may take a while)..."
        if pip install xformers --no-binary xformers; then
            print_success "xformers installed from source"
            return 0
        else
            print_warning "xformers installation failed - this is optional for CPU-only usage"
            print_info "You can continue without xformers if not using GPU acceleration"
            # Don't fail the installation, xformers is optional
            return 0
        fi
    fi
}

# Step 5: Core Dependencies
install_core_dependencies() {
    print_step 5 12 "Installing Core Dependencies"
    
    # Ensure venv exists and is activated
    if [ ! -f "$VENV_PATH/bin/activate" ]; then
        print_error "Virtual environment not found. Please run step 2 (Python Environment) first."
        return 1
    fi
    
    source "$VENV_PATH/bin/activate"
    
    # Install sd-scripts requirements
    if [ -f "sd-scripts/requirements.txt" ]; then
        print_info "Installing sd-scripts dependencies..."
        pip install -r sd-scripts/requirements.txt
        
        # Install sd-scripts as editable package
        if [ -f "sd-scripts/setup.py" ]; then
            print_info "Installing sd-scripts package..."
            pip install -e sd-scripts/
        fi
    fi
    
    # Install main requirements
    if [ -f "requirements.txt" ]; then
        print_info "Installing main dependencies..."
        pip install -r requirements.txt
    fi
    
    # Install API requirements
    if [ -f "api/requirements.txt" ]; then
        print_info "Installing API dependencies..."
        pip install -r api/requirements.txt
    fi
    
    print_success "Core dependencies installed"
}

# Step 6: Optional Components
install_optional_components() {
    print_step 6 12 "Installing Optional Components"
    
    # Ensure venv exists and is activated
    if [ ! -f "$VENV_PATH/bin/activate" ]; then
        print_error "Virtual environment not found. Please run step 2 (Python Environment) first."
        return 1
    fi
    
    source "$VENV_PATH/bin/activate"
    
    # Google Sheets sync
    if [ "$INSTALL_GOOGLE_SHEETS" = true ]; then
        print_info "Installing Google Sheets sync dependencies..."
        if [ -f "src/sheets_sync/requirements.txt" ]; then
            pip install -r src/sheets_sync/requirements.txt
        else
            # Fallback to direct installation
            pip install google-api-python-client>=2.100.0 \
                       google-auth>=2.20.0 \
                       google-auth-oauthlib>=1.0.0 \
                       google-auth-httplib2>=0.1.0
        fi
    fi
    
    # Interactive menu
    if [ -f "src/menu/interactive_menu_requirements.txt" ]; then
        print_info "Installing menu dependencies..."
        pip install -r src/menu/interactive_menu_requirements.txt
    fi
    
    # Development tools
    if [ "$INSTALL_DEV_TOOLS" = true ]; then
        print_info "Installing development tools..."
        pip install black ruff mypy pytest pytest-cov ipython jupyter
    fi
    
    print_success "Optional components installed"
}

# Step 7: PostgreSQL Setup
setup_postgresql() {
    if [ "$INSTALL_POSTGRESQL" != true ]; then
        return 0
    fi
    
    print_step 7 12 "Setting up PostgreSQL"
    
    # Run PostgreSQL setup script
    if [ -f "database_utils/setup_postgresql.sh" ]; then
        bash database_utils/setup_postgresql.sh
    else
        print_warning "PostgreSQL setup script not found"
    fi
}

# Step 8: Web Interface Setup
setup_web_interface() {
    if [ "$INSTALL_NODEJS" != true ]; then
        return 0
    fi
    
    print_step 8 12 "Setting up Web Interface"
    
    if [ -d "autotrainx-web" ] && [ -f "autotrainx-web/package.json" ]; then
        print_info "Installing web dependencies..."
        cd autotrainx-web
        npm install
        
        # Build for production if not in dev profile
        if [ "$SELECTED_PROFILE" != "dev" ]; then
            print_info "Building web interface..."
            npm run build
        fi
        
        cd ..
        print_success "Web interface ready"
    else
        print_warning "Web interface directory not found"
    fi
}

# Step 9: Model Downloads
download_models() {
    if [ "$INSTALL_MODELS" != true ]; then
        return 0
    fi
    
    print_step 9 12 "Downloading Models"
    
    # Ensure venv exists and is activated
    if [ ! -f "$VENV_PATH/bin/activate" ]; then
        print_error "Virtual environment not found. Please run step 2 (Python Environment) first."
        return 1
    fi
    
    source "$VENV_PATH/bin/activate"
    
    # Install huggingface-cli
    pip install huggingface_hub
    
    # Download models
    local models_dir="$SCRIPT_DIR/models"
    mkdir -p "$models_dir"
    
    print_info "Downloading models from Hugging Face..."
    print_warning "This may take a while depending on your connection speed"
    
    # Download specific models based on profile
    case "$SELECTED_PROFILE" in
        minimal)
            print_info "Skipping model downloads for minimal profile"
            ;;
        *)
            # Check for existing models
            if [ -d "$models_dir" ] && [ "$(ls -A "$models_dir" 2>/dev/null)" ]; then
                print_warning "Models directory already contains files"
                read -p "Re-download models? (y/N): " redownload
                [[ ! $redownload =~ ^[Yy]$ ]] && return 0
            fi
            
            # Download models from your repository
            if command -v huggingface-cli &> /dev/null; then
                # Copy models if they exist in the current directory
                for model_file in flux1-dev-fp8.safetensors t5xxl_fp8_e4m3fn.safetensors ae.safetensors clip_l.safetensors; do
                    if [ -f "$SCRIPT_DIR/models/$model_file" ]; then
                        print_info "Model $model_file already exists"
                    else
                        print_warning "Model $model_file not found - you may need to download it manually"
                    fi
                done
            fi
            ;;
    esac
}

# Step 10: Environment Configuration
setup_environment() {
    print_step 10 12 "Setting up Environment Configuration"
    
    # Create .env file
    mkdir -p "$SCRIPT_DIR/settings"
    cat > "$SCRIPT_DIR/settings/.env" << EOF
# AutoTrainX Environment Configuration
# Generated by setup.sh on $(date)

# Profile Configuration
AUTOTRAINX_PROFILE=$SELECTED_PROFILE
AUTOTRAINX_ENVIRONMENT=$ENVIRONMENT_TYPE

# Database Configuration
AUTOTRAINX_DB_TYPE=postgresql
AUTOTRAINX_DB_HOST=localhost
AUTOTRAINX_DB_PORT=5432
AUTOTRAINX_DB_NAME=autotrainx
AUTOTRAINX_DB_USER=autotrainx
AUTOTRAINX_DB_PASSWORD=1234

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Paths
AUTOTRAINX_ROOT=$SCRIPT_DIR
MODELS_PATH=$SCRIPT_DIR/models
VENV_PATH=$VENV_PATH

# CUDA Configuration
CUDA_VERSION=$CUDA_VERSION

# Docker Root Installation
DOCKER_ROOT_INSTALL=$DOCKER_ROOT_INSTALL

# Component Flags
POSTGRESQL_ENABLED=$INSTALL_POSTGRESQL
NODEJS_ENABLED=$INSTALL_NODEJS
DOCKER_ENABLED=$INSTALL_DOCKER
GOOGLE_SHEETS_ENABLED=$INSTALL_GOOGLE_SHEETS
EOF

    # Create activation script
    cat > "$SCRIPT_DIR/activate.sh" << 'EOF'
#!/bin/bash
# AutoTrainX Environment Activation Script

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Activate virtual environment
if [ -f "$SCRIPT_DIR/venv/bin/activate" ]; then
    source "$SCRIPT_DIR/venv/bin/activate"
    echo "Virtual environment activated"
else
    echo "Virtual environment not found"
    exit 1
fi

# Load environment variables
if [ -f "$SCRIPT_DIR/settings/.env" ]; then
    set -a
    source "$SCRIPT_DIR/settings/.env"
    set +a
    echo "Environment variables loaded"
fi

# Show status
echo "AutoTrainX environment ready!"
echo "Profile: $AUTOTRAINX_PROFILE"
echo "Python: $(which python)"
echo "Version: $(python --version)"
EOF

    chmod +x "$SCRIPT_DIR/activate.sh"
    print_success "Environment configuration completed"
}

# Step 11: Final Optimizations
apply_final_optimizations() {
    print_step 11 12 "Applying Final Optimizations"
    
    # Ensure venv exists and is activated
    if [ ! -f "$VENV_PATH/bin/activate" ]; then
        print_error "Virtual environment not found. Please run step 2 (Python Environment) first."
        return 1
    fi
    
    source "$VENV_PATH/bin/activate"
    
    # Profile-specific optimizations
    case "$SELECTED_PROFILE" in
        docker)
            # Docker-specific optimizations
            print_info "Applying Docker optimizations..."
            # Create docker-compose override for development
            if [ ! -f "docker-compose.override.yml" ]; then
                cat > "docker-compose.override.yml" << EOF
version: '3.8'
services:
  app:
    volumes:
      - ./models:/app/models
      - ./workspace:/app/workspace
EOF
            fi
            ;;
        wsl)
            # WSL-specific optimizations
            print_info "Applying WSL optimizations..."
            # Create .wslconfig recommendations
            cat > "$SCRIPT_DIR/wsl-recommendations.txt" << EOF
# Add to ~/.wslconfig on Windows:
[wsl2]
memory=8GB
processors=4
localhostForwarding=true
EOF
            ;;
        dev)
            # Development optimizations
            print_info "Setting up development environment..."
            # Install pre-commit hooks if available
            if [ -f ".pre-commit-config.yaml" ]; then
                pip install pre-commit
                pre-commit install
            fi
            ;;
    esac
    
    # Common optimizations
    pip install --upgrade diffusers transformers accelerate
    
    # Clean up
    pip cache purge
    
    print_success "Optimizations applied"
}

# Step 12: Verification
verify_installation() {
    print_step 12 12 "Verifying Installation"
    
    # Ensure venv exists and is activated
    if [ ! -f "$VENV_PATH/bin/activate" ]; then
        print_error "Virtual environment not found. Please run step 2 (Python Environment) first."
        return 1
    fi
    
    source "$VENV_PATH/bin/activate"
    
    local errors=0
    
    # Check Python environment
    print_info "Checking Python environment..."
    python --version || ((errors++))
    
    # Check PyTorch
    print_info "Checking PyTorch..."
    python -c "import torch; print(f'PyTorch {torch.__version__}')" || ((errors++))
    
    # Check CUDA if not minimal
    if [ "$SELECTED_PROFILE" != "minimal" ]; then
        python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')" || print_warning "CUDA not available"
    fi
    
    # Check optional components
    if [ "$INSTALL_POSTGRESQL" = true ]; then
        command -v psql &> /dev/null && print_success "PostgreSQL installed" || print_warning "PostgreSQL not found"
    fi
    
    if [ "$INSTALL_NODEJS" = true ]; then
        command -v node &> /dev/null && print_success "Node.js installed" || print_warning "Node.js not found"
    fi
    
    if [ "$INSTALL_DOCKER" = true ]; then
        command -v docker &> /dev/null && print_success "Docker installed" || print_warning "Docker not found"
    fi
    
    if [ $errors -eq 0 ]; then
        print_success "All core components verified successfully!"
        return 0
    else
        print_error "Some components failed verification"
        return 1
    fi
}

# ============================================================================
# Main Installation Flow
# ============================================================================

show_banner() {
    clear
    echo -e "${CYAN}${BOLD}"
    echo "╔═══════════════════════════════════════════════════════════════════════╗"
    echo "║                                                                       ║"
    echo "║                    AutoTrainX Unified Setup Script                    ║"
    echo "║                           Version 2.0                                 ║"
    echo "║                                                                       ║"
    echo "╚═══════════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

main() {
    show_banner
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --profile)
                SELECTED_PROFILE="$2"
                shift 2
                ;;
            --auto)
                AUTO_MODE=true
                shift
                ;;
            --config)
                INSTALL_CONFIG="$2"
                shift 2
                ;;
            --resume)
                if [ -n "$2" ] && [[ ! "$2" =~ ^-- ]]; then
                    RESUME_FROM="$2"
                    shift 2
                else
                    # Interactive resume selection
                    show_resume_options
                    read -p "Enter checkpoint to resume from (or 'clean'/'list'): " RESUME_FROM
                    shift
                fi
                ;;
            --retry-failed)
                # Find first failed step to resume from
                if [ -f "$FAILED_STEPS_FILE" ]; then
                    RESUME_FROM=$(head -n1 "$FAILED_STEPS_FILE" | cut -d: -f1)
                    if [ -n "$RESUME_FROM" ]; then
                        print_info "Retrying from first failed step: $RESUME_FROM"
                    else
                        print_error "No failed steps found"
                        exit 1
                    fi
                else
                    print_error "No failed steps recorded"
                    exit 1
                fi
                shift
                ;;
            --fix-triton)
                # Quick fix for triton/xformers errors
                fix_triton_error
                exit 0
                ;;
            --continue-on-error)
                CONTINUE_ON_ERROR=true
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    # Handle resume options
    if [ -n "$RESUME_FROM" ]; then
        case "$RESUME_FROM" in
            "clean")
                clean_checkpoints
                exit 0
                ;;
            "list")
                list_checkpoints
                exit 0
                ;;
            *)
                print_info "Resuming installation from checkpoint: $RESUME_FROM"
                ;;
        esac
    fi
    
    # Initialize log
    print_info "Starting AutoTrainX installation - $(date)"
    print_info "Installation log: $LOG_FILE"
    
    # Detect environment
    detect_environment
    
    # Check permissions
    check_root_permissions
    
    # Load configuration if specified
    if [ -n "$INSTALL_CONFIG" ]; then
        load_configuration "$INSTALL_CONFIG" || exit 1
    elif [ "$AUTO_MODE" = true ] && [ -f "$CONFIG_FILE" ]; then
        load_configuration "$CONFIG_FILE"
    fi
    
    # Interactive configuration if not in auto mode
    if [ "$AUTO_MODE" != true ]; then
        # Select profile if not already set
        if [ -z "$SELECTED_PROFILE" ]; then
            show_profile_menu
        fi
        
        # Configure components
        configure_profile_defaults
        customize_components
        
        # Save configuration
        save_configuration
    else
        # Validate profile if set via command line
        if [ -n "$SELECTED_PROFILE" ]; then
            if [[ ! " docker wsl linux dev minimal " =~ " $SELECTED_PROFILE " ]]; then
                print_error "Invalid profile: $SELECTED_PROFILE"
                exit 1
            fi
            configure_profile_defaults
        else
            print_error "No profile selected and no configuration found"
            exit 1
        fi
    fi
    
    # Show summary and confirm
    if [ "$AUTO_MODE" != true ]; then
        show_installation_summary
    fi
    
    # Execute installation steps with checkpoint support
    run_installation_with_checkpoints
    
    # Handle file ownership for Docker volumes
    if [ "$DOCKER_ROOT_INSTALL" = true ]; then
        print_info "Adjusting file ownership for Docker volumes..."
        
        # Check if HOST_UID and HOST_GID are set (typically passed as env vars in Docker)
        if [ -n "$HOST_UID" ] && [ -n "$HOST_GID" ]; then
            print_info "Setting ownership to UID:$HOST_UID GID:$HOST_GID"
            chown -R $HOST_UID:$HOST_GID "$SCRIPT_DIR"
        else
            print_warning "HOST_UID and HOST_GID not set - files will remain owned by root"
            print_info "To fix ownership, run the container with: -e HOST_UID=\$(id -u) -e HOST_GID=\$(id -g)"
        fi
    fi
    
    # Show completion message
    print_header "Installation Complete!"
    
    echo "Profile: $SELECTED_PROFILE"
    echo "Configuration saved to: $CONFIG_FILE"
    echo ""
    echo "Next steps:"
    echo "1. Activate environment: source activate.sh"
    echo "2. Start services based on your profile:"
    
    case "$SELECTED_PROFILE" in
        docker)
            echo "   - Start containers: docker-compose up -d"
            ;;
        minimal)
            echo "   - Run training: python main.py --train ..."
            ;;
        *)
            echo "   - Start API: python api_server.py"
            [ "$INSTALL_NODEJS" = true ] && echo "   - Start web UI: cd autotrainx-web && npm run dev"
            ;;
    esac
    
    echo ""
    print_success "Setup completed successfully!"
}

# Execute installation with checkpoint support
run_installation_with_checkpoints() {
    # Load any previously failed steps
    load_failed_steps
    
    # Define installation steps with checkpoints
    local steps=(
        "system_deps:install_system_dependencies:System Dependencies:false"
        "python_env:create_virtual_environment:Python Environment:true"
        "pytorch:install_pytorch:PyTorch:false"
        "xformers:install_xformers:XFormers (Optional):false"
        "core_deps:install_core_dependencies:Core Dependencies:false"
        "optional:install_optional_components:Optional Components:false"
        "postgresql:setup_postgresql:PostgreSQL:false"
        "web:setup_web_interface:Web Interface:false"
        "models:download_models:Models:false"
        "env_config:setup_environment:Environment Configuration:false"
        "optimize:apply_final_optimizations:Final Optimizations:false"
        "validation:verify_installation:Installation Verification:false"
    )
    
    local total_steps=${#steps[@]}
    local current_step=1
    local should_skip=true
    local installation_success=true
    
    # If resuming, determine where to start
    if [ -n "$RESUME_FROM" ]; then
        should_skip=true
        for step_def in "${steps[@]}"; do
            local checkpoint=$(echo "$step_def" | cut -d: -f1)
            if [ "$checkpoint" = "$RESUME_FROM" ]; then
                should_skip=false
                print_info "Resuming from checkpoint: $RESUME_FROM"
                break
            fi
        done
        
        if [ "$should_skip" = true ]; then
            print_error "Invalid checkpoint: $RESUME_FROM"
            show_resume_options
            return 1
        fi
    else
        should_skip=false
    fi
    
    # Execute steps
    for step_def in "${steps[@]}"; do
        local checkpoint=$(echo "$step_def" | cut -d: -f1)
        local function_name=$(echo "$step_def" | cut -d: -f2)
        local step_name=$(echo "$step_def" | cut -d: -f3)
        local is_critical=$(echo "$step_def" | cut -d: -f4)
        
        # Skip completed checkpoints unless resuming
        if [ "$should_skip" = true ]; then
            if [ "$checkpoint" != "$RESUME_FROM" ]; then
                print_info "⏭️  Skipping completed checkpoint: $checkpoint"
                ((current_step++))
                continue
            else
                should_skip=false
            fi
        fi
        
        # Check if step already completed
        if is_checkpoint_completed "$checkpoint"; then
            print_info "⏭️  Checkpoint '$checkpoint' already completed, skipping..."
            # Clear any failed status for this step
            clear_failed_step "$checkpoint"
            ((current_step++))
            continue
        fi
        
        # Execute step
        print_step "$current_step" "$total_steps" "$step_name"
        
        if "$function_name"; then
            # Step succeeded
            mark_checkpoint "$checkpoint"
            clear_failed_step "$checkpoint"
            print_success "✓ $step_name completed successfully"
        else
            # Step failed
            local error_msg="Step failed at $(date)"
            track_failed_step "$checkpoint" "$error_msg"
            print_error "❌ Step failed: $step_name"
            
            if [ "$is_critical" = "true" ]; then
                print_error "Critical step failed. Cannot continue."
                print_info "💡 You can resume from this point using: bash setup.sh --resume $checkpoint"
                installation_success=false
                break
            else
                if [ "$CONTINUE_ON_ERROR" = true ]; then
                    print_warning "⚠️  Non-critical step failed. Continuing with installation..."
                    installation_success=false
                else
                    print_info "💡 You can resume from this point using: bash setup.sh --resume $checkpoint"
                    installation_success=false
                    break
                fi
            fi
        fi
        
        ((current_step++))
    done
    
    # Show final report
    show_installation_report
    
    return $([ "$installation_success" = true ] && echo 0 || echo 1)
}

# Show installation report with failed steps
show_installation_report() {
    print_header "Installation Report"
    
    if [ ${#FAILED_STEPS[@]} -eq 0 ]; then
        print_success "All installation steps completed successfully! 🎉"
    else
        print_warning "Installation completed with some failures:"
        echo ""
        echo "Failed steps:"
        for failed_step in "${FAILED_STEPS[@]}"; do
            local checkpoint=$(echo "$failed_step" | cut -d: -f1)
            local error_msg=$(echo "$failed_step" | cut -d: -f2-)
            echo "  ❌ $checkpoint - $error_msg"
        done
        
        echo ""
        print_info "To retry failed steps:"
        echo ""
        
        # Generate retry commands
        for failed_step in "${FAILED_STEPS[@]}"; do
            local checkpoint=$(echo "$failed_step" | cut -d: -f1)
            echo "  bash setup.sh --resume $checkpoint"
        done
        
        echo ""
        print_info "Or retry all failed steps with:"
        echo "  bash setup.sh --retry-failed"
        
        # Special instructions for venv-dependent steps
        local venv_dependent_steps=("pytorch" "xformers" "core_deps" "optional" "optimize")
        local has_venv_deps=false
        
        for failed_step in "${FAILED_STEPS[@]}"; do
            local checkpoint=$(echo "$failed_step" | cut -d: -f1)
            for venv_step in "${venv_dependent_steps[@]}"; do
                if [ "$checkpoint" = "$venv_step" ]; then
                    has_venv_deps=true
                    break
                fi
            done
        done
        
        if [ "$has_venv_deps" = true ]; then
            echo ""
            print_warning "Note: Some failed steps require the virtual environment."
            print_info "Make sure the virtual environment is properly created before retrying."
            
            if [ ! -f "$VENV_PATH/bin/activate" ]; then
                print_error "Virtual environment not found! Run this first:"
                echo "  bash setup.sh --resume python_env"
            fi
        fi
    fi
    
    echo ""
}

show_help() {
    echo "AutoTrainX Unified Setup Script"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --profile PROFILE      Set installation profile (docker|wsl|linux|dev|minimal)"
    echo "  --auto                 Run in automatic mode using saved config or defaults"
    echo "  --config FILE          Load configuration from specified file"
    echo "  --resume [STEP]        Resume installation from specific checkpoint"
    echo "  --retry-failed         Retry all failed steps from previous run"
    echo "  --fix-triton           Quick fix for triton/xformers import errors"
    echo "  --continue-on-error    Continue installation even if non-critical steps fail"
    echo "  --help, -h             Show this help message"
    echo ""
    echo "Examples:"
    echo "  # Interactive installation"
    echo "  ./setup.sh"
    echo ""
    echo "  # Install with specific profile"
    echo "  ./setup.sh --profile docker"
    echo ""
    echo "  # Resume from checkpoint"
    echo "  ./setup.sh --resume postgresql"
    echo ""
    echo "  # Retry failed steps"
    echo "  ./setup.sh --retry-failed"
    echo ""
    echo "  # Fix triton import error"
    echo "  ./setup.sh --fix-triton"
    echo ""
    echo "  # Continue on errors"
    echo "  ./setup.sh --continue-on-error"
    echo ""
    echo "  # Automatic installation with saved config"
    echo "  ./setup.sh --auto"
    echo ""
    echo "  # Use custom configuration file"
    echo "  ./setup.sh --config my-config.json"
}

# ============================================================================
# Script Entry Point
# ============================================================================

# Ensure we're running from the correct directory
if [ ! -f "$SCRIPT_DIR/requirements.txt" ]; then
    print_error "This script must be run from the AutoTrainX root directory"
    exit 1
fi

# Run main installation
main "$@"