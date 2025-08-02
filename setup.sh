#!/bin/bash
#
# Interactive AutoTrainV2 Installation Script
#
# This script provides an interactive installation process with debugging options.
# Features:
# - Interactive prompts for each step
# - Detailed error handling and debugging
# - Option to skip failed steps
# - Rollback capabilities
# - Progress tracking
# - System requirements checking
#
# Usage:
#   bash install.sh [--auto] [--debug] [--skip-checks]
#
# Options:
#   --auto        Run in automatic mode (no prompts)
#   --debug       Enable verbose debugging output
#   --skip-checks Skip system requirement checks
#

set -e # Exit immediately if a command exits with a non-zero status.

# Global variables
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="$SCRIPT_DIR/venv"
LOG_FILE="$SCRIPT_DIR/install.log"
AUTO_MODE=false
DEBUG_MODE=false
SKIP_CHECKS=false
INSTALLATION_STEPS=()
FAILED_STEPS=()

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --auto)
            AUTO_MODE=true
            shift
            ;;
        --debug)
            DEBUG_MODE=true
            shift
            ;;
        --skip-checks)
            SKIP_CHECKS=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [--auto] [--debug] [--skip-checks]"
            echo "  --auto        Run in automatic mode (no prompts)"
            echo "  --debug       Enable verbose debugging output"
            echo "  --skip-checks Skip system requirement checks"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Function to print colored messages
print_info() {
    echo -e "\n\e[34m\e[1m[INFO]\e[0m $1\e[0m" | tee -a "$LOG_FILE"
}

print_success() {
    echo -e "\e[32m\e[1m[SUCCESS]\e[0m $1\e[0m" | tee -a "$LOG_FILE"
}

print_warning() {
    echo -e "\e[33m\e[1m[WARNING]\e[0m $1\e[0m" | tee -a "$LOG_FILE"
}

print_error() {
    echo -e "\e[31m\e[1m[ERROR]\e[0m $1\e[0m" | tee -a "$LOG_FILE"
}

print_debug() {
    if [ "$DEBUG_MODE" = true ]; then
        echo -e "\e[35m\e[1m[DEBUG]\e[0m $1\e[0m" | tee -a "$LOG_FILE"
    fi
}

print_step() {
    echo -e "\n\e[36m\e[1m[STEP $1]\e[0m $2\e[0m" | tee -a "$LOG_FILE"
}

# Function to ask user for confirmation
ask_confirmation() {
    if [ "$AUTO_MODE" = true ]; then
        return 0
    fi
    
    local message="$1"
    local default="${2:-y}"
    
    while true; do
        read -p "$message (y/n, default: $default): " yn
        yn=${yn:-$default}
        case $yn in
            [Yy]* ) return 0;;
            [Nn]* ) return 1;;
            * ) echo "Please answer yes or no.";;
        esac
    done
}

# Function to handle step failure
handle_step_failure() {
    local step_name="$1"
    local error_message="$2"
    
    FAILED_STEPS+=("$step_name")
    print_error "Step '$step_name' failed: $error_message"
    
    if [ "$DEBUG_MODE" = true ]; then
        print_debug "Last 10 lines of log:"
        tail -n 10 "$LOG_FILE"
    fi
    
    echo ""
    echo "Options:"
    echo "1. Retry this step"
    echo "2. Skip this step (may cause issues later)"
    echo "3. Debug this step"
    echo "4. Abort installation"
    
    if [ "$AUTO_MODE" = true ]; then
        print_warning "Auto mode: Skipping failed step '$step_name'"
        return 1
    fi
    
    while true; do
        read -p "Choose an option (1-4): " choice
        case $choice in
            1) return 0;; # Retry
            2) return 1;; # Skip
            3) debug_step "$step_name"; continue;;
            4) cleanup_and_exit;;
            *) echo "Invalid choice. Please select 1-4.";;
        esac
    done
}

# Function to debug a specific step
debug_step() {
    local step_name="$1"
    
    print_info "Debugging step: $step_name"
    echo "Available debug options:"
    echo "1. Show detailed logs"
    echo "2. Check system requirements"
    echo "3. Check disk space"
    echo "4. Check network connectivity"
    echo "5. Check Python environment"
    echo "6. Return to main menu"
    
    while true; do
        read -p "Choose debug option (1-6): " choice
        case $choice in
            1) show_detailed_logs;;
            2) check_system_requirements;;
            3) check_disk_space;;
            4) check_network_connectivity;;
            5) check_python_environment;;
            6) return;;
            *) echo "Invalid choice. Please select 1-6.";;
        esac
    done
}

# Debug helper functions
show_detailed_logs() {
    print_info "Showing last 50 lines of installation log:"
    tail -n 50 "$LOG_FILE" | less
}

check_system_requirements() {
    print_info "Checking system requirements..."
    
    # Check OS
    echo "OS: $(uname -s)"
    echo "Architecture: $(uname -m)"
    
    # Check Python
    if command -v python3 &> /dev/null; then
        echo "Python3: $(python3 --version)"
    else
        print_error "Python3 not found!"
    fi
    
    # Check pip
    if command -v pip3 &> /dev/null; then
        echo "pip3: $(pip3 --version)"
    else
        print_error "pip3 not found!"
    fi
    
    # Check git
    if command -v git &> /dev/null; then
        echo "Git: $(git --version)"
    else
        print_warning "Git not found (may be needed for some dependencies)"
    fi
    
    # Check CUDA
    if command -v nvidia-smi &> /dev/null; then
        echo "NVIDIA Driver: $(nvidia-smi --query-gpu=driver_version --format=csv,noheader,nounits | head -1)"
        echo "CUDA Version: $(nvidia-smi --query-gpu=cuda_version --format=csv,noheader,nounits | head -1)"
    else
        print_warning "NVIDIA drivers not found or nvidia-smi not available"
    fi
}

check_disk_space() {
    print_info "Checking disk space..."
    df -h "$SCRIPT_DIR"
    
    # Check if we have at least 10GB free
    available_space=$(df "$SCRIPT_DIR" | awk 'NR==2 {print $4}')
    if [ "$available_space" -lt 10485760 ]; then # 10GB in KB
        print_warning "Less than 10GB available space. Installation may fail."
    fi
}

check_network_connectivity() {
    print_info "Checking network connectivity..."
    
    # Check general internet connectivity
    if ping -c 1 google.com &> /dev/null; then
        print_success "Internet connectivity: OK"
    else
        print_error "No internet connectivity!"
        return 1
    fi
    
    # Check PyPI
    if curl -s --head https://pypi.org/ | head -n 1 | grep -q "200 OK"; then
        print_success "PyPI accessibility: OK"
    else
        print_warning "PyPI may not be accessible"
    fi
    
    # Check Hugging Face
    if curl -s --head https://huggingface.co/ | head -n 1 | grep -q "200 OK"; then
        print_success "Hugging Face accessibility: OK"
    else
        print_warning "Hugging Face may not be accessible"
    fi
}

check_python_environment() {
    print_info "Checking Python environment..."
    
    if [ -d "$VENV_PATH" ]; then
        print_info "Virtual environment exists at: $VENV_PATH"
        if [ -f "$VENV_PATH/bin/activate" ]; then
            print_success "Virtual environment appears to be valid"
            
            # Check if we can activate it
            if source "$VENV_PATH/bin/activate" 2>/dev/null; then
                print_success "Virtual environment can be activated"
                echo "Python in venv: $(which python)"
                echo "Python version: $(python --version)"
                deactivate
            else
                print_error "Cannot activate virtual environment"
            fi
        else
            print_error "Virtual environment is corrupted"
        fi
    else
        print_info "Virtual environment does not exist yet"
    fi
}

# Function to cleanup and exit
cleanup_and_exit() {
    print_info "Cleaning up..."
    
    if ask_confirmation "Remove incomplete virtual environment?"; then
        if [ -d "$VENV_PATH" ]; then
            rm -rf "$VENV_PATH"
            print_success "Virtual environment removed"
        fi
    fi
    
    if [ ${#FAILED_STEPS[@]} -gt 0 ]; then
        print_error "Installation failed. Failed steps: ${FAILED_STEPS[*]}"
    fi
    
    print_info "Installation log saved to: $LOG_FILE"
    exit 1
}

# Function to execute a step with error handling
execute_step() {
    local step_number="$1"
    local step_name="$2"
    local step_function="$3"
    
    print_step "$step_number" "$step_name"
    INSTALLATION_STEPS+=("$step_name")
    
    while true; do
        print_debug "Executing function: $step_function"
        
        # Ensure virtual environment is activated for each step (except creation/activation steps)
        if [ "$step_number" -gt 3 ] && [ -f "$VENV_PATH/bin/activate" ]; then
            if source "$VENV_PATH/bin/activate" 2>/dev/null && $step_function 2>&1 | tee -a "$LOG_FILE"; then
                print_success "Step '$step_name' completed successfully"
                return 0
            else
                if handle_step_failure "$step_name" "Function $step_function failed"; then
                    continue # Retry
                else
                    return 1 # Skip
                fi
            fi
        else
            if $step_function 2>&1 | tee -a "$LOG_FILE"; then
                print_success "Step '$step_name' completed successfully"
                return 0
            else
                if handle_step_failure "$step_name" "Function $step_function failed"; then
                    continue # Retry
                else
                    return 1 # Skip
                fi
            fi
        fi
    done
}

# Installation step functions
step_check_prerequisites() {
    print_info "Checking prerequisites..."
    
    # Check if running from correct directory
    if [ ! -f "$SCRIPT_DIR/install.sh" ]; then
        print_error "Please run this script from the project root directory"
        return 1
    fi
    
    # Check current user
    current_user=$(whoami)
    print_info "Running as user: $current_user"
    
    if [ "$current_user" = "root" ]; then
        print_warning "Running as root user."
        print_info "The installation will proceed with root privileges."
        print_info "Virtual environment will be created with appropriate permissions."
        
        # Set a flag for root installation
        export RUNNING_AS_ROOT=true
        
        if ! ask_confirmation "Continue installation as root?"; then
            print_info "Installation cancelled."
            return 1
        fi
    else
        export RUNNING_AS_ROOT=false
        
        # Check if sudo is available for non-root users
        if ! command -v sudo &> /dev/null; then
            print_error "sudo is not installed and you're not running as root"
            print_info "You have two options:"
            print_info "  1. Install sudo and run the script again"
            print_info "  2. Run the script as root: su root -c './setup.sh'"
            return 1
        fi
        
        # Test if user has sudo privileges
        if ! sudo -n true 2>/dev/null; then
            print_info "Testing sudo access..."
            if ! sudo true; then
                print_error "Failed to obtain sudo privileges"
                print_info "Please ensure your user has sudo access or run as root"
                return 1
            fi
        fi
    fi
    
    # Check Python 3
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is required but not installed"
        return 1
    fi
    
    # Check pip
    if ! command -v pip3 &> /dev/null; then
        print_error "pip3 is required but not installed"
        return 1
    fi
    
    # Check minimum Python version (3.8+)
    python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    python_major=$(python3 -c "import sys; print(sys.version_info.major)")
    python_minor=$(python3 -c "import sys; print(sys.version_info.minor)")
    
    # Check if Python version is 3.8 or higher
    if [ "$python_major" -lt 3 ] || ([ "$python_major" -eq 3 ] && [ "$python_minor" -lt 8 ]); then
        print_error "Python 3.8 or higher is required (found: $python_version)"
        return 1
    fi
    
    # Check CUDA availability
    if command -v nvidia-smi &> /dev/null; then
        print_info "NVIDIA GPU detected: $(nvidia-smi --query-gpu=name --format=csv,noheader,nounits | head -1)"
        print_info "CUDA Version: $(nvidia-smi --query-gpu=cuda_version --format=csv,noheader,nounits | head -1)"
    else
        print_warning "NVIDIA drivers not found. CUDA acceleration may not be available."
    fi
    
    print_success "Prerequisites check passed"
    return 0
}

step_create_venv() {
    print_info "Creating Python virtual environment in '$VENV_PATH'..."
    
    # Remove existing venv if it exists and is corrupted
    if [ -d "$VENV_PATH" ]; then
        if ! [ -f "$VENV_PATH/bin/activate" ]; then
            print_warning "Removing corrupted virtual environment..."
            rm -rf "$VENV_PATH"
        elif ask_confirmation "Virtual environment already exists. Recreate it?"; then
            rm -rf "$VENV_PATH"
        else
            print_info "Using existing virtual environment"
            return 0
        fi
    fi
    
    # Create virtual environment with special handling for root
    if [ "$RUNNING_AS_ROOT" = true ]; then
        print_info "Creating virtual environment as root with --system-site-packages..."
        python3 -m venv "$VENV_PATH" --system-site-packages
        
        # Set more permissive permissions for root-created venv
        chmod -R 755 "$VENV_PATH"
    else
        python3 -m venv "$VENV_PATH"
    fi
    
    # Verify venv creation
    if [ ! -f "$VENV_PATH/bin/activate" ]; then
        print_error "Failed to create virtual environment"
        return 1
    fi
    
    print_success "Virtual environment created successfully"
    return 0
}

step_activate_venv() {
    print_info "Activating virtual environment..."
    
    if [ ! -f "$VENV_PATH/bin/activate" ]; then
        print_error "Virtual environment not found at $VENV_PATH"
        return 1
    fi
    
    # Source the activation script
    source "$VENV_PATH/bin/activate"
    
    # Verify activation
    if [ "$VIRTUAL_ENV" != "$VENV_PATH" ]; then
        print_error "Failed to activate virtual environment"
        return 1
    fi
    
    print_success "Virtual environment activated"
    print_debug "Python path: $(which python)"
    print_debug "Python version: $(python --version)"
    return 0
}

step_upgrade_pip() {
    print_info "Upgrading pip to latest version..."
    
    # Ensure we're in the virtual environment
    if [ -z "$VIRTUAL_ENV" ]; then
        source "$VENV_PATH/bin/activate"
    fi
    
    print_debug "Pip path: $(which pip)"
    
    pip install --upgrade pip
    
    print_success "pip upgraded successfully"
    print_debug "pip version: $(pip --version)"
    return 0
}

step_install_xformers() {
    print_info "Installing xformers..."
    
    # Ensure we're in the virtual environment
    if [ -z "$VIRTUAL_ENV" ]; then
        source "$VENV_PATH/bin/activate"
    fi
    
    print_debug "Python path: $(which python)"
    print_debug "Pip path: $(which pip)"
    
    # Uninstall any existing xformers installation
    print_info "Cleaning up any existing xformers installation..."
    pip uninstall -y xformers 2>/dev/null || true
    
    # Install build dependencies first
    print_info "Installing build dependencies..."
    pip install wheel setuptools ninja
    
    # Try to install pre-built xformers first (faster and more reliable)
    print_info "Attempting to install pre-built xformers..."
    if pip install xformers --index-url https://download.pytorch.org/whl/cu128 2>/dev/null; then
        print_success "Pre-built xformers installed successfully"
    else
        print_warning "Pre-built xformers failed, trying source installation..."
        print_info "This may take 15-30 minutes depending on your system..."
        
        # Fallback to source installation
        if pip install xformers --no-binary xformers -v; then
            print_success "xformers installed successfully from source"
        else
            print_error "Both pre-built and source xformers installation failed"
            print_warning "Continuing without xformers - you may need to install it manually later"
            return 0  # Don't fail the entire installation
        fi
    fi
    
    # Verify installation
    print_info "Verifying xformers installation..."
    if python -c "import xformers; print(f'xformers {xformers.__version__} installed successfully'); print(f'Location: {xformers.__file__}')" 2>/dev/null; then
        print_success "xformers verification passed"
        return 0
    else
        print_error "xformers installation verification failed"
        print_warning "xformers may not be working properly, but continuing installation..."
        return 0  # Don't fail the entire installation for xformers issues
    fi
}

step_install_sd_scripts_requirements() {
    print_info "Installing dependencies from sd-scripts/requirements.txt..."
    
    # Ensure we're in the virtual environment
    if [ -z "$VIRTUAL_ENV" ]; then
        source "$VENV_PATH/bin/activate"
    fi
    
    if [ ! -f "sd-scripts/requirements.txt" ]; then
        print_warning "sd-scripts/requirements.txt not found. Skipping this step."
        return 0
    fi
    
    # Change to sd-scripts directory and install requirements
    (cd sd-scripts && source "$VENV_PATH/bin/activate" && pip install -r requirements.txt)
    
    print_success "Dependencies from sd-scripts/requirements.txt installed"
    return 0
}

step_install_main_requirements() {
    print_info "Installing dependencies from requirements.txt..."
    
    # Ensure we're in the virtual environment
    if [ -z "$VIRTUAL_ENV" ]; then
        source "$VENV_PATH/bin/activate"
    fi
    
    if [ ! -f "requirements.txt" ]; then
        print_warning "requirements.txt not found. Skipping this step."
        return 0
    fi
    
    # Install requirements with dependency resolution
    print_info "Installing requirements with dependency resolution..."
    pip install -r requirements.txt --upgrade
    
    # Try to resolve any dependency conflicts
    print_info "Checking for dependency conflicts..."
    if pip check 2>/dev/null; then
        print_success "No dependency conflicts found"
    else
        print_warning "Some dependency conflicts exist, but continuing..."
        pip check || true  # Show conflicts but don't fail
    fi
    
    print_success "Dependencies from requirements.txt installed"
    return 0
}

step_install_api_requirements() {
    print_info "Installing API dependencies from api/requirements.txt..."
    
    # Ensure we're in the virtual environment
    if [ -z "$VIRTUAL_ENV" ]; then
        source "$VENV_PATH/bin/activate"
    fi
    
    if [ ! -f "api/requirements.txt" ]; then
        print_warning "api/requirements.txt not found. Skipping this step."
        return 0
    fi
    
    # Install API requirements
    print_info "Installing FastAPI and related dependencies..."
    pip install -r api/requirements.txt --upgrade
    
    print_success "API dependencies installed"
    return 0
}

step_install_sheets_sync_requirements() {
    print_info "Installing Google Sheets sync dependencies..."
    
    # Ensure we're in the virtual environment
    if [ -z "$VIRTUAL_ENV" ]; then
        source "$VENV_PATH/bin/activate"
    fi
    
    if [ ! -f "src/sheets_sync/requirements.txt" ]; then
        print_warning "src/sheets_sync/requirements.txt not found. Skipping this step."
        return 0
    fi
    
    # Install Google Sheets dependencies
    print_info "Installing Google Sheets API dependencies..."
    pip install -r src/sheets_sync/requirements.txt --upgrade
    
    print_success "Google Sheets sync dependencies installed"
    return 0
}

step_install_menu_requirements() {
    print_info "Installing interactive menu dependencies..."
    
    # Ensure we're in the virtual environment
    if [ -z "$VIRTUAL_ENV" ]; then
        source "$VENV_PATH/bin/activate"
    fi
    
    if [ ! -f "src/menu/interactive_menu_requirements.txt" ]; then
        print_warning "src/menu/interactive_menu_requirements.txt not found. Skipping this step."
        return 0
    fi
    
    # Install menu requirements
    pip install -r src/menu/interactive_menu_requirements.txt --upgrade
    
    print_success "Interactive menu dependencies installed"
    return 0
}

step_install_system_dependencies() {
    print_info "Checking and installing system dependencies..."
    
    # Check if running on Linux/Ubuntu/WSL2
    if [ ! -f /etc/os-release ]; then
        print_warning "Cannot detect OS. Skipping system dependencies."
        return 0
    fi
    
    . /etc/os-release
    
    if [[ "$ID" != "ubuntu" && "$ID" != "debian" ]]; then
        print_warning "System dependencies installation is only supported on Ubuntu/Debian. Detected: $ID"
        return 0
    fi
    
    # Function to run commands with appropriate privileges
    run_privileged() {
        if [ "$RUNNING_AS_ROOT" = true ]; then
            # Running as root, execute directly
            "$@"
        else
            # Not root, check if sudo is available
            if command -v sudo &> /dev/null; then
                sudo "$@"
            else
                print_error "This command requires root privileges but sudo is not available"
                print_info "Please run the script as root or install sudo"
                return 1
            fi
        fi
    }
    
    # Check if PostgreSQL is already installed
    if command -v psql &> /dev/null; then
        print_info "PostgreSQL is already installed"
    else
        if ask_confirmation "Install PostgreSQL for database support?"; then
            print_info "Installing PostgreSQL..."
            if run_privileged apt-get update && run_privileged apt-get install -y postgresql postgresql-contrib; then
                print_success "PostgreSQL installed"
            else
                print_error "Failed to install PostgreSQL"
                print_info "You may need to install it manually"
            fi
        else
            print_warning "Skipping PostgreSQL installation. You may need to install it manually for full functionality."
        fi
    fi
    
    # Check for Node.js (needed for web interface)
    if command -v node &> /dev/null; then
        print_info "Node.js is already installed: $(node --version)"
    else
        if ask_confirmation "Install Node.js for web interface support?"; then
            print_info "Installing Node.js..."
            local install_success=false
            
            if [ "$RUNNING_AS_ROOT" = true ]; then
                # Running as root, execute directly
                if curl -fsSL https://deb.nodesource.com/setup_lts.x | bash - && apt-get install -y nodejs; then
                    install_success=true
                fi
            else
                # Not root, use sudo
                if command -v sudo &> /dev/null; then
                    if curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash - && sudo apt-get install -y nodejs; then
                        install_success=true
                    fi
                else
                    print_error "Node.js installation requires root privileges but sudo is not available"
                    print_info "Please run the script as root or install sudo"
                fi
            fi
            
            if [ "$install_success" = true ]; then
                print_success "Node.js installed"
            else
                print_error "Failed to install Node.js"
                print_info "You may need to install it manually"
            fi
        else
            print_warning "Skipping Node.js installation. Web interface will not be available."
        fi
    fi
    
    # Install other useful system packages
    print_info "Installing additional system packages..."
    run_privileged apt-get install -y \
        build-essential \
        git \
        wget \
        curl \
        htop \
        ncdu \
        tree \
        jq \
        make || print_warning "Some system packages failed to install, but continuing..."
    
    print_success "System dependencies check completed"
    return 0
}

step_setup_postgresql() {
    print_info "Setting up PostgreSQL database..."
    
    # Check if PostgreSQL is installed
    if ! command -v psql &> /dev/null; then
        print_warning "PostgreSQL is not installed. Skipping database setup."
        return 0
    fi
    
    if ask_confirmation "Configure PostgreSQL for AutoTrainX?"; then
        # Run the PostgreSQL setup script if it exists
        if [ -f "database_utils/setup_postgresql.sh" ]; then
            print_info "Running PostgreSQL setup script..."
            bash database_utils/setup_postgresql.sh
        else
            print_warning "PostgreSQL setup script not found. Manual configuration may be required."
        fi
    else
        print_info "Skipping PostgreSQL configuration"
    fi
    
    return 0
}

step_install_web_dependencies() {
    print_info "Installing web interface dependencies..."
    
    # Check if Node.js is installed
    if ! command -v node &> /dev/null; then
        print_warning "Node.js is not installed. Skipping web dependencies."
        return 0
    fi
    
    # Check if autotrainx-web directory exists
    if [ ! -d "autotrainx-web" ]; then
        print_warning "autotrainx-web directory not found. Skipping web dependencies."
        return 0
    fi
    
    # Check if package.json exists
    if [ ! -f "autotrainx-web/package.json" ]; then
        print_warning "autotrainx-web/package.json not found. Skipping web dependencies."
        return 0
    fi
    
    if ask_confirmation "Install web interface dependencies (Next.js, React, etc.)?"; then
        print_info "Installing Node.js dependencies..."
        cd autotrainx-web
        
        # Install dependencies
        npm install
        
        # Return to original directory
        cd ..
        
        print_success "Web interface dependencies installed"
        
        # Build the web interface
        if ask_confirmation "Build the web interface for production?"; then
            print_info "Building web interface..."
            cd autotrainx-web
            npm run build
            cd ..
            print_success "Web interface built successfully"
        fi
    else
        print_info "Skipping web interface dependencies"
    fi
    
    return 0
}

step_install_pytorch() {
    print_info "Installing PyTorch for CUDA 12.8..."
    
    # Ensure we're in the virtual environment
    if [ -z "$VIRTUAL_ENV" ]; then
        source "$VENV_PATH/bin/activate"
    fi
    
    # Check current Python and pip paths
    print_debug "Python path: $(which python)"
    print_debug "Pip path: $(which pip)"
    print_debug "Virtual env: $VIRTUAL_ENV"
    print_debug "Current user: $(whoami)"
    
    # Handle root installation
    if [ "$RUNNING_AS_ROOT" = true ]; then
        print_info "Installing PyTorch as root user."
    fi
    
    # Uninstall any existing PyTorch installations to avoid conflicts
    print_info "Cleaning up any existing PyTorch installations..."
    pip uninstall -y torch torchvision torchaudio xformers 2>/dev/null || true
    
    # Install latest PyTorch with CUDA 12.8 support (exact command as requested)
    print_info "Installing latest PyTorch with CUDA 12.8 support..."
    print_info "Using command: pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128"
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
    
    # Install opencv-python to resolve dependency conflicts
    print_info "Installing opencv-python to resolve dependency conflicts..."
    pip install opencv-python>=4.6.0
    
    # Verify PyTorch installation in virtual environment
    print_info "Verifying PyTorch installation..."
    if ! python -c "import torch; print(f'PyTorch {torch.__version__} installed'); print(f'Location: {torch.__file__}')" 2>/dev/null; then
        print_error "PyTorch installation verification failed"
        return 1
    fi
    
    # Verify CUDA availability
    if ! python -c "import torch; assert torch.cuda.is_available(), 'CUDA not available'; print(f'CUDA {torch.version.cuda} available with {torch.cuda.device_count()} GPU(s)')" 2>/dev/null; then
        print_warning "CUDA is not available or not working properly"
    fi
    
    # Verify it's installed in the virtual environment (if using venv)
    if [ -n "$VIRTUAL_ENV" ]; then
        pytorch_location=$(python -c "import torch; print(torch.__file__)")
        if [[ "$pytorch_location" == *"$VENV_PATH"* ]]; then
            print_success "PyTorch is correctly installed in virtual environment"
        else
            print_warning "PyTorch location: $pytorch_location (may not be in venv due to root execution)"
        fi
    fi
    
    print_success "PyTorch for CUDA 12.8 installed successfully"
    return 0
}

step_install_huggingface_hub() {
    print_info "Installing huggingface_hub for model downloads..."
    
    # Ensure we're in the virtual environment
    if [ -z "$VIRTUAL_ENV" ]; then
        source "$VENV_PATH/bin/activate"
    fi
    
    pip install huggingface_hub
    
    print_success "huggingface_hub installed successfully"
    return 0
}

step_download_models() {
    print_info "Model Download Configuration"
    print_warning "The models from 'EQX55/trainX' are large files and may take significant time to download."
    print_info "You can skip this step now and download the models later using:"
    print_info "  huggingface-cli download EQX55/trainX --repo-type model --local-dir models/trainX"
    
    if ! ask_confirmation "Do you want to download the models now?"; then
        print_info "Skipping model download. You can download them later."
        return 0
    fi
    
    print_info "Downloading models from Hugging Face repository 'EQX55/trainX'..."
    
    # Ensure we're in the virtual environment
    if [ -z "$VIRTUAL_ENV" ]; then
        source "$VENV_PATH/bin/activate"
    fi
    
    local models_dir="$SCRIPT_DIR/models/trainX"
    
    # Create models directory if it doesn't exist
    mkdir -p "$(dirname "$models_dir")"
    
    # Check if models already exist
    if [ -d "$models_dir" ] && [ "$(ls -A "$models_dir")" ]; then
        if ask_confirmation "Models directory already exists and is not empty. Re-download?"; then
            rm -rf "$models_dir"
        else
            print_info "Using existing models"
            return 0
        fi
    fi
    
    # Download models with progress indication
    huggingface-cli download EQX55/trainX --repo-type model --local-dir "$models_dir" --local-dir-use-symlinks False
    
    # Verify download
    if [ ! -d "$models_dir" ] || [ ! "$(ls -A "$models_dir")" ]; then
        print_error "Model download failed or directory is empty"
        return 1
    fi
    
    print_success "Models downloaded successfully to '$models_dir'"
    return 0
}

step_final_fixes() {
    print_info "Applying final fixes..."
    
    # Ensure we're in the virtual environment
    if [ -z "$VIRTUAL_ENV" ]; then
        source "$VENV_PATH/bin/activate"
    fi
    
    # Upgrade diffusers to latest version
    print_info "Upgrading diffusers to latest version..."
    pip install --upgrade diffusers
    
    # Install GPUtil for GPU monitoring
    print_info "Installing GPUtil for GPU monitoring..."
    pip install GPUtil
    
    # Uninstall bitsandbytes (known to cause issues in some configurations)
    print_info "Uninstalling bitsandbytes..."
    pip uninstall -y bitsandbytes 2>/dev/null || true
    
    print_success "Final fixes completed successfully"
    return 0
}

step_setup_environment_variables() {
    print_info "Setting up environment variables..."
    
    # Create a .env file for the project if it doesn't exist
    if [ ! -f "$SCRIPT_DIR/.env" ]; then
        print_info "Creating .env file with default configuration..."
        cat > "$SCRIPT_DIR/.env" << EOF
# AutoTrainX Environment Configuration
# Generated by setup.sh on $(date)

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

# Python Virtual Environment
VIRTUAL_ENV_PATH=$VENV_PATH
EOF
        print_success ".env file created"
    else
        print_info ".env file already exists"
    fi
    
    # Add activation script
    if [ ! -f "$SCRIPT_DIR/activate.sh" ]; then
        print_info "Creating activation script..."
        cat > "$SCRIPT_DIR/activate.sh" << EOF
#!/bin/bash
# AutoTrainX Activation Script
# Source this file to activate the virtual environment and set environment variables

# Get the directory of this script
SCRIPT_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="\$SCRIPT_DIR/venv"

# Check if running as root
if [ "\$(whoami)" = "root" ]; then
    echo "Note: Running as root user"
fi

# Activate virtual environment
if [ -f "\$VENV_PATH/bin/activate" ]; then
    source "\$VENV_PATH/bin/activate"
    echo "Virtual environment activated"
else
    echo "Virtual environment not found at \$VENV_PATH"
    exit 1
fi

# Load environment variables
if [ -f "\$SCRIPT_DIR/.env" ]; then
    export \$(grep -v '^#' "\$SCRIPT_DIR/.env" | xargs)
    echo "Environment variables loaded"
else
    echo "Warning: .env file not found"
fi

echo "AutoTrainX environment is ready!"
echo "Python: \$(which python)"
echo "Python version: \$(python --version)"
echo "User: \$(whoami)"
EOF
        chmod +x "$SCRIPT_DIR/activate.sh"
        print_success "Activation script created"
    fi
    
    print_info "To activate the AutoTrainX environment in the future, run:"
    print_info "  source $SCRIPT_DIR/activate.sh"
    
    return 0
}

step_verify_installation() {
    print_info "Running comprehensive verification checks..."
    
    # Ensure we're in the virtual environment
    if [ -z "$VIRTUAL_ENV" ]; then
        source "$VENV_PATH/bin/activate"
    fi
    
    local verification_failed=false
    
    # Check Python version and location
    print_info "Python version: $(python --version)"
    print_info "Python location: $(which python)"
    print_info "Virtual environment: $VIRTUAL_ENV"
    
    # Check PyTorch and CUDA
    if python -c "import torch; print(f'PyTorch version: {torch.__version__}'); print(f'PyTorch location: {torch.__file__}'); assert torch.cuda.is_available(), 'CUDA not available'" 2>/dev/null; then
        pytorch_version=$(python -c "import torch; print(torch.__version__)")
        pytorch_location=$(python -c "import torch; print(torch.__file__)")
        cuda_version=$(python -c "import torch; print(torch.version.cuda)")
        gpu_count=$(python -c "import torch; print(torch.cuda.device_count())")
        print_success "PyTorch ($pytorch_version) with CUDA ($cuda_version) - $gpu_count GPU(s) available"
        print_info "PyTorch location: $pytorch_location"
        
        # Verify PyTorch is in virtual environment
        if [[ "$pytorch_location" == *"$VENV_PATH"* ]]; then
            print_success "PyTorch is correctly installed in virtual environment"
        else
            print_warning "PyTorch may not be installed in virtual environment"
        fi
    else
        print_error "PyTorch is not correctly installed or CUDA is not available"
        verification_failed=true
    fi
    
    # Check xformers
    if python -c "import xformers; print(f'xformers version: {xformers.__version__}'); print(f'xformers location: {xformers.__file__}')" 2>/dev/null; then
        xformers_version=$(python -c "import xformers; print(xformers.__version__)")
        xformers_location=$(python -c "import xformers; print(xformers.__file__)")
        print_success "xformers ($xformers_version) is installed and working"
        print_info "xformers location: $xformers_location"
    else
        print_error "xformers is not installed or not working"
        verification_failed=true
    fi
    
    # Check diffusers
    if python -c "import diffusers; print(f'diffusers version: {diffusers.__version__}')" 2>/dev/null; then
        diffusers_version=$(python -c "import diffusers; print(diffusers.__version__)")
        print_success "diffusers ($diffusers_version) is installed and working"
    else
        print_warning "diffusers is not installed or not working"
    fi
    
    # Check Gradio
    if python -c "import gradio; print(f'Gradio version: {gradio.__version__}')" 2>/dev/null; then
        gradio_version=$(python -c "import gradio; print(gradio.__version__)")
        print_success "Gradio ($gradio_version) is installed"
    else
        print_warning "Gradio is not installed"
    fi
    
    # Check FastAPI
    if python -c "import fastapi; print(f'FastAPI version: {fastapi.__version__}')" 2>/dev/null; then
        fastapi_version=$(python -c "import fastapi; print(fastapi.__version__)")
        print_success "FastAPI ($fastapi_version) is installed"
    else
        print_warning "FastAPI is not installed"
    fi
    
    # Check SQLAlchemy
    if python -c "import sqlalchemy; print(f'SQLAlchemy version: {sqlalchemy.__version__}')" 2>/dev/null; then
        sqlalchemy_version=$(python -c "import sqlalchemy; print(sqlalchemy.__version__)")
        print_success "SQLAlchemy ($sqlalchemy_version) is installed"
    else
        print_warning "SQLAlchemy is not installed"
    fi
    
    # Check PostgreSQL
    if command -v psql &> /dev/null; then
        psql_version=$(psql --version | awk '{print $3}')
        print_success "PostgreSQL ($psql_version) is installed"
        
        # Check if AutoTrainX database exists
        if [ "$RUNNING_AS_ROOT" = true ]; then
            if su - postgres -c "psql -lqt" | cut -d \| -f 1 | grep -qw autotrainx; then
                print_success "AutoTrainX database exists"
            else
                print_warning "AutoTrainX database not configured"
            fi
        else
            if sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw autotrainx; then
                print_success "AutoTrainX database exists"
            else
                print_warning "AutoTrainX database not configured"
            fi
        fi
    else
        print_warning "PostgreSQL is not installed"
    fi
    
    # Check Node.js and npm
    if command -v node &> /dev/null; then
        node_version=$(node --version)
        print_success "Node.js ($node_version) is installed"
        
        if command -v npm &> /dev/null; then
            npm_version=$(npm --version)
            print_success "npm ($npm_version) is installed"
        else
            print_warning "npm is not installed"
        fi
        
        # Check if web dependencies are installed
        if [ -d "autotrainx-web/node_modules" ]; then
            print_success "Web interface dependencies are installed"
        else
            print_warning "Web interface dependencies not installed"
        fi
    else
        print_warning "Node.js is not installed"
    fi
    
    # Check models
    if [ -d "$SCRIPT_DIR/models/trainX" ] && [ "$(ls -A "$SCRIPT_DIR/models/trainX")" ]; then
        model_count=$(find "$SCRIPT_DIR/models/trainX" -type f | wc -l)
        print_success "Models directory exists with $model_count files"
    else
        print_warning "Models directory is missing or empty"
        print_info "You can download models later with:"
        print_info "  huggingface-cli download EQX55/trainX --repo-type model --local-dir models/trainX"
        # Don't mark as failed since models can be downloaded later
    fi
    
    # Summary of optional components
    print_info "\nOptional Components Status:"
    print_info "- PostgreSQL: $(command -v psql &> /dev/null && echo "Installed" || echo "Not installed")"
    print_info "- Node.js: $(command -v node &> /dev/null && echo "Installed" || echo "Not installed")"
    print_info "- Web Interface: $([ -d "autotrainx-web/node_modules" ] && echo "Ready" || echo "Not ready")"
    print_info "- API Server: $(python -c "import fastapi" 2>/dev/null && echo "Ready" || echo "Not ready")"
    
    if [ "$verification_failed" = true ]; then
        print_error "Some core verification checks failed"
        return 1
    else
        print_success "All core verification checks passed!"
        return 0
    fi
}

# Main installation function
main() {
    # Initialize log file
    echo "AutoTrainV2 Installation Log - $(date)" > "$LOG_FILE"
    
    print_info "Starting AutoTrainV2 Interactive Installation"
    print_info "Script directory: $SCRIPT_DIR"
    print_info "Log file: $LOG_FILE"
    
    if [ "$AUTO_MODE" = true ]; then
        print_info "Running in automatic mode"
    fi
    
    if [ "$DEBUG_MODE" = true ]; then
        print_info "Debug mode enabled"
    fi
    
    # Show installation summary
    echo ""
    echo "Installation Steps:"
    echo "1. Check Prerequisites"
    echo "2. Install System Dependencies"
    echo "3. Create Virtual Environment"
    echo "4. Activate Virtual Environment"
    echo "5. Upgrade pip"
    echo "6. Install PyTorch for CUDA 12.8"
    echo "7. Install xformers"
    echo "8. Install sd-scripts requirements"
    echo "9. Install main requirements"
    echo "10. Install API requirements"
    echo "11. Install Google Sheets sync requirements"
    echo "12. Install menu requirements"
    echo "13. Install Hugging Face Hub"
    echo "14. Download Models"
    echo "15. Setup PostgreSQL Database"
    echo "16. Install Web Interface Dependencies"
    echo "17. Final Fixes"
    echo "18. Setup Environment Variables"
    echo "19. Verify Installation"
    echo ""
    
    if ! ask_confirmation "Proceed with installation?"; then
        print_info "Installation cancelled by user"
        exit 0
    fi
    
    # Execute installation steps
    execute_step 1 "Check Prerequisites" step_check_prerequisites || true
    execute_step 2 "Install System Dependencies" step_install_system_dependencies || true
    execute_step 3 "Create Virtual Environment" step_create_venv || true
    execute_step 4 "Activate Virtual Environment" step_activate_venv || true
    execute_step 5 "Upgrade pip" step_upgrade_pip || true
    execute_step 6 "Install PyTorch for CUDA 12.8" step_install_pytorch || true
    execute_step 7 "Install xformers" step_install_xformers || true
    execute_step 8 "Install sd-scripts requirements" step_install_sd_scripts_requirements || true
    execute_step 9 "Install main requirements" step_install_main_requirements || true
    execute_step 10 "Install API requirements" step_install_api_requirements || true
    execute_step 11 "Install Google Sheets sync requirements" step_install_sheets_sync_requirements || true
    execute_step 12 "Install menu requirements" step_install_menu_requirements || true
    execute_step 13 "Install Hugging Face Hub" step_install_huggingface_hub || true
    execute_step 14 "Download Models" step_download_models || true
    execute_step 15 "Setup PostgreSQL Database" step_setup_postgresql || true
    execute_step 16 "Install Web Interface Dependencies" step_install_web_dependencies || true
    execute_step 17 "Final Fixes" step_final_fixes || true
    execute_step 18 "Setup Environment Variables" step_setup_environment_variables || true
    execute_step 19 "Verify Installation" step_verify_installation || true
    
    # Final summary
    echo ""
    print_info "Installation Summary:"
    print_info "Completed steps: ${#INSTALLATION_STEPS[@]}"
    
    if [ ${#FAILED_STEPS[@]} -gt 0 ]; then
        print_warning "Failed steps: ${FAILED_STEPS[*]}"
    else
        print_success "All steps completed successfully!"
    fi
    
    print_info ""
    print_info "Installation log saved to: $LOG_FILE"
    
    if [ ${#FAILED_STEPS[@]} -eq 0 ]; then
        print_success "AutoTrainX installation completed successfully!"
        print_info ""
        print_info "To start using AutoTrainX:"
        print_info "  1. Activate the environment: source $SCRIPT_DIR/activate.sh"
        print_info "  2. Start the API server: python api/main.py"
        print_info "  3. Start the web interface: cd autotrainx-web && npm run dev"
        print_info "  4. Or use the interactive menu: python src/menu/interactive_menu.py"
        print_info ""
        print_info "Quick start commands:"
        print_info "  - Activate environment: source activate.sh"
        print_info "  - Start all services: ./start_dev.sh"
        print_info "  - Stop all services: ./stop_dev.sh"
        exit 0
    else
        print_error "Installation completed with some failures. Check the log for details."
        print_warning "Failed steps: ${FAILED_STEPS[*]}"
        print_info ""
        print_info "You can try to fix the issues and run the setup again."
        print_info "To run specific steps, modify the script or install dependencies manually."
        exit 1
    fi
}

# Trap signals for cleanup
trap cleanup_and_exit SIGINT SIGTERM

# Run main function
main "$@"