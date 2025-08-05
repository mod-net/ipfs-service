#!/bin/bash

# IPFS (Kubo) Installation Script
# This script downloads, installs, and sets up IPFS Kubo for the Module Registry integration

set -e  # Exit on any error

echo "🚀 IPFS (Kubo) Installation Script"
echo "=================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
KUBO_VERSION="v0.28.0"
ARCH="linux-amd64"
DOWNLOAD_URL="https://dist.ipfs.tech/kubo/${KUBO_VERSION}/kubo_${KUBO_VERSION}_${ARCH}.tar.gz"
TEMP_DIR="/tmp/ipfs-install"
INSTALL_DIR="/usr/local/bin"

# Functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

check_command() {
    if command -v "$1" >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Check if running as root for installation
check_sudo() {
    if [[ $EUID -eq 0 ]]; then
        log_warning "Running as root. This is fine for installation."
        SUDO=""
    else
        if check_command sudo; then
            SUDO="sudo"
            log_info "Will use sudo for installation steps that require root access."
        else
            log_error "This script requires sudo access to install IPFS to ${INSTALL_DIR}"
            exit 1
        fi
    fi
}

# Check if IPFS is already installed
check_existing_ipfs() {
    if check_command ipfs; then
        EXISTING_VERSION=$(ipfs version --number 2>/dev/null || echo "unknown")
        log_warning "IPFS is already installed (version: ${EXISTING_VERSION})"
        echo -n "Do you want to reinstall? [y/N]: "
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            log_info "Skipping installation. Proceeding to initialization check..."
            return 1
        fi
    fi
    return 0
}

# Download and install IPFS
install_ipfs() {
    log_info "Creating temporary directory..."
    mkdir -p "$TEMP_DIR"
    cd "$TEMP_DIR"

    log_info "Downloading IPFS Kubo ${KUBO_VERSION}..."
    if check_command wget; then
        wget -q --show-progress "$DOWNLOAD_URL"
    elif check_command curl; then
        curl -L -o "kubo_${KUBO_VERSION}_${ARCH}.tar.gz" "$DOWNLOAD_URL"
    else
        log_error "Neither wget nor curl found. Please install one of them."
        exit 1
    fi

    log_info "Extracting archive..."
    tar -xzf "kubo_${KUBO_VERSION}_${ARCH}.tar.gz"

    log_info "Installing IPFS to ${INSTALL_DIR}..."
    cd kubo
    $SUDO bash install.sh

    log_success "IPFS installed successfully!"
}

# Initialize IPFS repository
init_ipfs() {
    if [[ -d "$HOME/.ipfs" ]]; then
        log_warning "IPFS repository already exists at $HOME/.ipfs"
        echo -n "Do you want to reinitialize? [y/N]: "
        read -r response
        if [[ "$response" =~ ^[Yy]$ ]]; then
            log_info "Removing existing repository..."
            rm -rf "$HOME/.ipfs"
        else
            log_info "Keeping existing repository."
            return 0
        fi
    fi

    log_info "Initializing IPFS repository..."
    ipfs init

    log_success "IPFS repository initialized!"
}

# Test IPFS installation
test_ipfs() {
    log_info "Testing IPFS installation..."
    
    if ! check_command ipfs; then
        log_error "IPFS command not found after installation!"
        return 1
    fi

    VERSION=$(ipfs version --number)
    log_success "IPFS version: ${VERSION}"

    # Test basic functionality
    log_info "Testing basic IPFS functionality..."
    TEST_CONTENT="Hello, IPFS! This is a test from the Module Registry installation script."
    TEST_CID=$(echo "$TEST_CONTENT" | ipfs add -q)
    
    if [[ -n "$TEST_CID" ]]; then
        log_success "Basic IPFS functionality test passed (CID: ${TEST_CID})"
        
        # Clean up test content
        ipfs pin rm "$TEST_CID" >/dev/null 2>&1 || true
    else
        log_error "Basic IPFS functionality test failed!"
        return 1
    fi
}

# Start IPFS daemon
start_daemon() {
    log_info "Checking if IPFS daemon is already running..."
    
    if pgrep -f "ipfs daemon" >/dev/null; then
        log_warning "IPFS daemon is already running!"
        return 0
    fi

    echo -n "Do you want to start the IPFS daemon now? [Y/n]: "
    read -r response
    if [[ "$response" =~ ^[Nn]$ ]]; then
        log_info "Skipping daemon startup. You can start it later with: ipfs daemon"
        return 0
    fi

    log_info "Starting IPFS daemon..."
    log_warning "The daemon will run in the background. Use 'pkill -f \"ipfs daemon\"' to stop it."
    
    nohup ipfs daemon >/dev/null 2>&1 &
    DAEMON_PID=$!
    
    # Wait a moment for daemon to start
    sleep 3
    
    if kill -0 $DAEMON_PID 2>/dev/null; then
        log_success "IPFS daemon started successfully (PID: ${DAEMON_PID})"
        log_info "API available at: http://127.0.0.1:5001"
        log_info "Gateway available at: http://127.0.0.1:8080"
        log_info "WebUI available at: http://127.0.0.1:5001/webui"
    else
        log_error "Failed to start IPFS daemon!"
        return 1
    fi
}

# Cleanup function
cleanup() {
    if [[ -d "$TEMP_DIR" ]]; then
        log_info "Cleaning up temporary files..."
        rm -rf "$TEMP_DIR"
    fi
}

# Main installation process
main() {
    echo
    log_info "Starting IPFS installation process..."
    
    # Set up cleanup trap
    trap cleanup EXIT
    
    # Check prerequisites
    check_sudo
    
    # Check for existing installation
    if check_existing_ipfs; then
        install_ipfs
    fi
    
    # Initialize repository
    init_ipfs
    
    # Test installation
    test_ipfs
    
    # Optionally start daemon
    start_daemon
    
    echo
    log_success "IPFS installation completed successfully!"
    echo
    echo "📋 Next Steps:"
    echo "1. If not started, run: ipfs daemon"
    echo "2. Install commune-ipfs dependencies: cd commune-ipfs && uv pip install -e ."
    echo "3. Start the backend: cd commune-ipfs && uv run python main.py"
    echo "4. Test the integration: cd commune-ipfs && uv run python integration_client.py"
    echo
    echo "📚 Documentation: See README.md for detailed usage instructions"
    echo "🌐 IPFS WebUI: http://127.0.0.1:5001/webui (when daemon is running)"
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "IPFS (Kubo) Installation Script"
        echo
        echo "Usage: $0 [OPTIONS]"
        echo
        echo "Options:"
        echo "  --help, -h     Show this help message"
        echo "  --version, -v  Show version information"
        echo "  --uninstall    Uninstall IPFS"
        echo
        echo "This script will:"
        echo "1. Download and install IPFS Kubo"
        echo "2. Initialize the IPFS repository"
        echo "3. Test the installation"
        echo "4. Optionally start the IPFS daemon"
        exit 0
        ;;
    --version|-v)
        echo "IPFS Installation Script v1.0"
        echo "Installs IPFS Kubo ${KUBO_VERSION}"
        exit 0
        ;;
    --uninstall)
        log_info "Uninstalling IPFS..."
        if check_command ipfs; then
            # Stop daemon if running
            pkill -f "ipfs daemon" 2>/dev/null || true
            
            # Remove binary
            $SUDO rm -f "${INSTALL_DIR}/ipfs"
            
            echo -n "Do you want to remove the IPFS repository (~/.ipfs)? [y/N]: "
            read -r response
            if [[ "$response" =~ ^[Yy]$ ]]; then
                rm -rf "$HOME/.ipfs"
                log_success "IPFS repository removed"
            fi
            
            log_success "IPFS uninstalled successfully!"
        else
            log_warning "IPFS not found, nothing to uninstall"
        fi
        exit 0
        ;;
    "")
        # No arguments, proceed with installation
        main
        ;;
    *)
        log_error "Unknown option: $1"
        echo "Use --help for usage information"
        exit 1
        ;;
esac
