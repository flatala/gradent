#!/bin/bash

################################################################################
# Gradent Complete VM Deployment Script
# This script automates the ENTIRE deployment process on a fresh Ubuntu VM
# 
# Usage: 
#   1. Copy this script to your Ubuntu VM
#   2. Make it executable: chmod +x deploy-vm.sh
#   3. Run with: ./deploy-vm.sh
#   4. Follow the prompts to enter your OpenAI API key
#
# Or run in one command:
#   curl -o deploy-vm.sh https://raw.githubusercontent.com/flatala/gradent/main/deploy-vm.sh && chmod +x deploy-vm.sh && ./deploy-vm.sh
################################################################################

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Configuration
PROJECT_DIR="$HOME/gradent"
REPO_URL="https://github.com/flatala/gradent.git"

################################################################################
# Helper Functions
################################################################################

print_banner() {
    echo -e "${CYAN}${BOLD}"
    echo "╔═══════════════════════════════════════════════════════════════════╗"
    echo "║                                                                   ║"
    echo "║              GRADENT COMPLETE VM DEPLOYMENT                       ║"
    echo "║              Automated Setup Script v1.0                          ║"
    echo "║                                                                   ║"
    echo "╚═══════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_section() {
    echo ""
    echo -e "${MAGENTA}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${MAGENTA}${BOLD}  $1${NC}"
    echo -e "${MAGENTA}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

print_step() {
    echo -e "${CYAN}→ $1${NC}"
}

# Error handler
error_exit() {
    print_error "Error on line $1"
    print_error "Deployment failed. Please check the error messages above."
    exit 1
}

trap 'error_exit $LINENO' ERR

################################################################################
# Pre-flight Checks
################################################################################

preflight_checks() {
    print_section "Pre-flight Checks"
    
    # Check if running on Linux
    if [[ "$OSTYPE" != "linux-gnu"* ]]; then
        print_error "This script is designed for Linux (Ubuntu) systems only."
        exit 1
    fi
    print_success "Running on Linux"
    
    # Check if Ubuntu
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        if [[ "$ID" != "ubuntu" ]]; then
            print_warning "This script is designed for Ubuntu. Your distro: $ID"
            read -p "Continue anyway? (y/n) " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                exit 1
            fi
        else
            print_success "Ubuntu detected: $VERSION"
        fi
    fi
    
    # Check if running as root
    if [ "$EUID" -eq 0 ]; then
        print_warning "Please do not run this script as root (sudo)"
        print_info "The script will prompt for sudo password when needed"
        exit 1
    fi
    print_success "Not running as root"
    
    # Check sudo access
    if sudo -n true 2>/dev/null; then
        print_success "Sudo access confirmed"
    else
        print_info "Checking sudo access..."
        if sudo -v; then
            print_success "Sudo access confirmed"
        else
            print_error "This script requires sudo access"
            exit 1
        fi
    fi
    
    # Check internet connectivity
    if ping -c 1 8.8.8.8 &> /dev/null; then
        print_success "Internet connectivity confirmed"
    else
        print_error "No internet connectivity detected"
        exit 1
    fi
    
    # Check disk space (need at least 5GB)
    available_space=$(df / | awk 'NR==2 {print $4}')
    if [ "$available_space" -lt 5242880 ]; then
        print_warning "Low disk space. Available: $(df -h / | awk 'NR==2 {print $4}')"
        print_warning "Recommended: At least 10GB free space"
    else
        print_success "Sufficient disk space available"
    fi
    
    # Check RAM (need at least 2GB)
    total_ram=$(free -m | awk 'NR==2 {print $2}')
    if [ "$total_ram" -lt 2000 ]; then
        print_warning "Low RAM detected. Available: ${total_ram}MB"
        print_warning "Recommended: At least 2GB RAM"
    else
        print_success "Sufficient RAM available: ${total_ram}MB"
    fi
}

################################################################################
# System Update
################################################################################

update_system() {
    print_section "Step 1: Updating System Packages"
    
    print_step "Updating package lists..."
    sudo apt update -qq
    print_success "Package lists updated"
    
    print_step "Upgrading existing packages..."
    sudo DEBIAN_FRONTEND=noninteractive apt upgrade -y -qq
    print_success "System packages upgraded"
    
    print_step "Installing basic utilities..."
    sudo apt install -y -qq git curl wget vim ufw net-tools > /dev/null 2>&1
    print_success "Basic utilities installed"
}

################################################################################
# Firewall Configuration
################################################################################

configure_firewall() {
    print_section "Step 2: Configuring Firewall"
    
    print_step "Configuring UFW firewall..."
    
    # Check if UFW is already enabled
    if sudo ufw status | grep -q "Status: active"; then
        print_info "UFW is already active"
    else
        sudo ufw --force reset > /dev/null 2>&1
    fi
    
    # Allow SSH (important!)
    print_step "Allowing SSH (port 22)..."
    sudo ufw allow 22/tcp > /dev/null 2>&1
    print_success "SSH access allowed"
    
    # Allow HTTP
    print_step "Allowing HTTP (port 80)..."
    sudo ufw allow 80/tcp > /dev/null 2>&1
    print_success "HTTP access allowed"
    
    # Allow HTTPS
    print_step "Allowing HTTPS (port 443)..."
    sudo ufw allow 443/tcp > /dev/null 2>&1
    print_success "HTTPS access allowed"
    
    # Allow backend port (optional, for direct API access)
    print_step "Allowing Backend API (port 8000)..."
    sudo ufw allow 8000/tcp > /dev/null 2>&1
    print_success "Backend API access allowed"
    
    # Enable firewall
    print_step "Enabling firewall..."
    sudo ufw --force enable > /dev/null 2>&1
    print_success "Firewall enabled and configured"
}

################################################################################
# Docker Installation
################################################################################

install_docker() {
    print_section "Step 3: Installing Docker"
    
    # Check if Docker is already installed
    if command -v docker &> /dev/null; then
        DOCKER_VERSION=$(docker --version | awk '{print $3}' | sed 's/,//')
        print_info "Docker is already installed: $DOCKER_VERSION"
        read -p "Reinstall Docker? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_success "Skipping Docker installation"
            return
        fi
    fi
    
    print_step "Removing old Docker versions..."
    sudo apt remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true
    
    print_step "Installing Docker dependencies..."
    sudo apt install -y -qq \
        apt-transport-https \
        ca-certificates \
        curl \
        gnupg \
        lsb-release \
        software-properties-common > /dev/null 2>&1
    print_success "Dependencies installed"
    
    print_step "Adding Docker GPG key..."
    sudo mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
        sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg 2>/dev/null
    print_success "GPG key added"
    
    print_step "Adding Docker repository..."
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] \
        https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | \
        sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    print_success "Repository added"
    
    print_step "Installing Docker Engine..."
    sudo apt update -qq
    sudo apt install -y -qq \
        docker-ce \
        docker-ce-cli \
        containerd.io \
        docker-buildx-plugin \
        docker-compose-plugin > /dev/null 2>&1
    print_success "Docker Engine installed"
    
    print_step "Adding user to docker group..."
    sudo usermod -aG docker $USER
    print_success "User added to docker group"
    
    # Verify installation
    DOCKER_VERSION=$(docker --version | awk '{print $3}' | sed 's/,//')
    COMPOSE_VERSION=$(docker compose version | awk '{print $4}')
    print_success "Docker $DOCKER_VERSION installed"
    print_success "Docker Compose $COMPOSE_VERSION installed"
    
    print_warning "Note: You may need to log out and back in for docker group changes to take effect"
    print_info "Using newgrp to activate group in current session..."
}

################################################################################
# Clone Repository
################################################################################

clone_repository() {
    print_section "Step 4: Cloning Gradent Repository"
    
    if [ -d "$PROJECT_DIR" ]; then
        print_warning "Directory $PROJECT_DIR already exists"
        read -p "Delete and re-clone? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_step "Backing up existing .env file (if exists)..."
            if [ -f "$PROJECT_DIR/.env" ]; then
                cp "$PROJECT_DIR/.env" "$HOME/.env.backup"
                print_success "Backed up .env to $HOME/.env.backup"
            fi
            print_step "Removing existing directory..."
            rm -rf "$PROJECT_DIR"
            print_success "Existing directory removed"
        else
            print_info "Using existing directory"
            cd "$PROJECT_DIR"
            print_step "Pulling latest changes..."
            git pull
            print_success "Repository updated"
            return
        fi
    fi
    
    print_step "Cloning repository from $REPO_URL..."
    git clone "$REPO_URL" "$PROJECT_DIR" > /dev/null 2>&1
    print_success "Repository cloned to $PROJECT_DIR"
    
    cd "$PROJECT_DIR"
    
    # Restore .env if it was backed up
    if [ -f "$HOME/.env.backup" ]; then
        print_step "Restoring backed up .env file..."
        cp "$HOME/.env.backup" "$PROJECT_DIR/.env"
        rm "$HOME/.env.backup"
        print_success ".env file restored"
    fi
}

################################################################################
# Environment Configuration
################################################################################

configure_environment() {
    print_section "Step 5: Configuring Environment"
    
    cd "$PROJECT_DIR"
    
    if [ -f .env ]; then
        print_info ".env file already exists"
        read -p "Reconfigure? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            # Validate existing API key
            if grep -q "OPENAI_API_KEY=sk-" .env && ! grep -q "sk-your-" .env; then
                print_success "Using existing .env configuration"
                return
            else
                print_warning "Existing .env file doesn't have a valid API key"
            fi
        fi
    fi
    
    print_step "Creating .env file from template..."
    cp .env.example .env
    print_success ".env file created"
    
    # Prompt for OpenAI API key
    echo ""
    print_info "${BOLD}OpenAI API Key Configuration${NC}"
    print_info "You need an OpenAI API key to use this application"
    print_info "Get one at: https://platform.openai.com/api-keys"
    echo ""
    
    while true; do
        read -p "$(echo -e ${CYAN}Enter your OpenAI API key: ${NC})" OPENAI_KEY
        
        if [[ -z "$OPENAI_KEY" ]]; then
            print_error "API key cannot be empty"
            continue
        fi
        
        if [[ ! "$OPENAI_KEY" =~ ^sk- ]]; then
            print_error "Invalid API key format (should start with 'sk-')"
            continue
        fi
        
        # Update .env file
        sed -i "s/OPENAI_API_KEY=.*/OPENAI_API_KEY=$OPENAI_KEY/" .env
        print_success "OpenAI API key configured"
        break
    done
    
    # Optional configurations
    echo ""
    print_info "Optional configurations (press Enter to skip):"
    echo ""
    
    read -p "$(echo -e ${CYAN}Discord Webhook URL [optional]: ${NC})" DISCORD_URL
    if [[ ! -z "$DISCORD_URL" ]]; then
        echo "DISCORD_WEBHOOK_URL=$DISCORD_URL" >> .env
        print_success "Discord webhook configured"
    fi
    
    read -p "$(echo -e ${CYAN}Google Client ID [optional]: ${NC})" GOOGLE_ID
    if [[ ! -z "$GOOGLE_ID" ]]; then
        echo "GOOGLE_CLIENT_ID=$GOOGLE_ID" >> .env
        read -p "$(echo -e ${CYAN}Google Client Secret: ${NC})" GOOGLE_SECRET
        echo "GOOGLE_CLIENT_SECRET=$GOOGLE_SECRET" >> .env
        print_success "Google Calendar configured"
    fi
    
    print_success "Environment configuration complete"
}

################################################################################
# Create Necessary Directories
################################################################################

create_directories() {
    print_section "Step 6: Creating Directories"
    
    cd "$PROJECT_DIR"
    
    print_step "Creating data directories..."
    mkdir -p data logs uploads data/vector_db
    print_success "Directories created"
    
    # Set permissions
    print_step "Setting permissions..."
    chmod -R 755 data logs uploads
    print_success "Permissions set"
}

################################################################################
# Build and Deploy
################################################################################

build_and_deploy() {
    print_section "Step 7: Building and Deploying Application"
    
    cd "$PROJECT_DIR"
    
    print_step "Building Docker images (this may take 5-10 minutes)..."
    print_info "Building backend image..."
    
    # Use newgrp to ensure docker group is active
    sg docker -c "docker compose build --no-cache" 2>&1 | while IFS= read -r line; do
        if [[ "$line" =~ (Step|Successfully) ]]; then
            echo -e "${CYAN}  $line${NC}"
        fi
    done
    
    print_success "Docker images built successfully"
    
    print_step "Starting containers..."
    sg docker -c "docker compose up -d"
    print_success "Containers started"
    
    # Wait for containers to be ready
    print_step "Waiting for containers to be healthy..."
    sleep 5
    
    # Check container status
    if sg docker -c "docker compose ps | grep -q 'Up'"; then
        print_success "Containers are running"
    else
        print_error "Containers failed to start"
        sg docker -c "docker compose logs"
        exit 1
    fi
}

################################################################################
# Health Checks
################################################################################

perform_health_checks() {
    print_section "Step 8: Performing Health Checks"
    
    cd "$PROJECT_DIR"
    
    # Wait for services to fully start
    print_step "Waiting for services to initialize (30 seconds)..."
    sleep 10
    
    # Check backend health
    print_step "Checking backend health..."
    for i in {1..30}; do
        if curl -f http://localhost:8000/health &> /dev/null; then
            print_success "Backend is healthy ✓"
            break
        fi
        if [ $i -eq 30 ]; then
            print_error "Backend health check failed"
            print_warning "Check logs with: docker compose logs backend"
            return 1
        fi
        sleep 2
    done
    
    # Check frontend
    print_step "Checking frontend..."
    for i in {1..30}; do
        if curl -f http://localhost/ &> /dev/null; then
            print_success "Frontend is healthy ✓"
            break
        fi
        if [ $i -eq 30 ]; then
            print_error "Frontend health check failed"
            print_warning "Check logs with: docker compose logs frontend"
            return 1
        fi
        sleep 2
    done
    
    # Show container status
    print_step "Container status:"
    sg docker -c "docker compose ps"
}

################################################################################
# Initialize Database
################################################################################

initialize_database() {
    print_section "Step 9: Initializing Database"
    
    cd "$PROJECT_DIR"
    
    echo ""
    read -p "$(echo -e ${CYAN}Initialize database with mock data for testing? [Y/n]: ${NC})" -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        print_step "Initializing database with mock data..."
        if sg docker -c "docker compose exec backend python scripts/setup_all.py" > /dev/null 2>&1; then
            print_success "Database initialized with mock data"
        else
            print_warning "Database initialization failed (this is optional)"
            print_info "You can run it later with: docker compose exec backend python scripts/setup_all.py"
        fi
    else
        print_info "Skipping database initialization"
        print_info "You can initialize it later with: docker compose exec backend python scripts/setup_all.py"
    fi
}

################################################################################
# Display Summary
################################################################################

display_summary() {
    print_section "Deployment Complete! 🎉"
    
    # Get server IP
    SERVER_IP=$(hostname -I | awk '{print $1}')
    
    echo ""
    echo -e "${GREEN}${BOLD}✓ Gradent Study Assistant is now running!${NC}"
    echo ""
    echo -e "${CYAN}${BOLD}Access your application:${NC}"
    echo -e "  ${BOLD}Frontend:${NC}     http://$SERVER_IP/"
    echo -e "  ${BOLD}              or http://localhost/${NC}"
    echo ""
    echo -e "  ${BOLD}Backend API:${NC}  http://$SERVER_IP:8000"
    echo -e "  ${BOLD}              or http://localhost:8000${NC}"
    echo ""
    echo -e "  ${BOLD}API Docs:${NC}     http://$SERVER_IP:8000/docs"
    echo -e "  ${BOLD}              or http://localhost:8000/docs${NC}"
    echo ""
    
    echo -e "${YELLOW}${BOLD}Important Information:${NC}"
    echo -e "  ${BOLD}Project Directory:${NC} $PROJECT_DIR"
    echo -e "  ${BOLD}Configuration:${NC}     $PROJECT_DIR/.env"
    echo ""
    
    echo -e "${CYAN}${BOLD}Useful Commands:${NC}"
    echo -e "  ${BOLD}View logs:${NC}         cd $PROJECT_DIR && docker compose logs -f"
    echo -e "  ${BOLD}Stop services:${NC}     cd $PROJECT_DIR && docker compose down"
    echo -e "  ${BOLD}Restart services:${NC}  cd $PROJECT_DIR && docker compose restart"
    echo -e "  ${BOLD}Check status:${NC}      cd $PROJECT_DIR && docker compose ps"
    echo -e "  ${BOLD}Update app:${NC}        cd $PROJECT_DIR && git pull && docker compose up -d --build"
    echo ""
    
    echo -e "${MAGENTA}${BOLD}Quick Access Aliases (optional):${NC}"
    echo -e "  Add these to your ~/.bashrc for convenience:"
    echo -e "  ${CYAN}alias gradent-logs='cd $PROJECT_DIR && docker compose logs -f'${NC}"
    echo -e "  ${CYAN}alias gradent-restart='cd $PROJECT_DIR && docker compose restart'${NC}"
    echo -e "  ${CYAN}alias gradent-status='cd $PROJECT_DIR && docker compose ps'${NC}"
    echo ""
    
    echo -e "${GREEN}${BOLD}Next Steps:${NC}"
    echo -e "  1. Open http://$SERVER_IP/ in your browser"
    echo -e "  2. Test the chat interface"
    echo -e "  3. Explore the API at http://$SERVER_IP:8000/docs"
    echo -e "  4. For production, set up SSL (see deployment/DEPLOYMENT_GUIDE.md)"
    echo ""
    
    echo -e "${YELLOW}${BOLD}Documentation:${NC}"
    echo -e "  Full guide: $PROJECT_DIR/deployment/DEPLOYMENT_GUIDE.md"
    echo -e "  Quick ref:  $PROJECT_DIR/deployment/CHEATSHEET.txt"
    echo ""
    
    if [ "$total_ram" -lt 2000 ]; then
        echo -e "${YELLOW}${BOLD}⚠ Performance Warning:${NC}"
        echo -e "  Your system has limited RAM (${total_ram}MB)."
        echo -e "  Monitor performance with: ${CYAN}docker stats${NC}"
        echo ""
    fi
    
    echo -e "${GREEN}${BOLD}Deployment successful! Enjoy using Gradent! 🚀${NC}"
    echo ""
}

################################################################################
# Main Execution
################################################################################

main() {
    clear
    print_banner
    
    echo -e "${CYAN}This script will:${NC}"
    echo "  1. Update your system"
    echo "  2. Configure firewall"
    echo "  3. Install Docker & Docker Compose"
    echo "  4. Clone the Gradent repository"
    echo "  5. Configure environment variables"
    echo "  6. Build and deploy the application"
    echo "  7. Perform health checks"
    echo "  8. Initialize the database"
    echo ""
    
    read -p "$(echo -e ${YELLOW}Continue with deployment? [Y/n]: ${NC})" -n 1 -r
    echo
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        print_info "Deployment cancelled"
        exit 0
    fi
    
    echo ""
    print_info "Starting deployment..."
    sleep 2
    
    # Execute deployment steps
    preflight_checks
    update_system
    configure_firewall
    install_docker
    clone_repository
    configure_environment
    create_directories
    build_and_deploy
    perform_health_checks
    initialize_database
    display_summary
    
    # Save deployment info
    cat > "$PROJECT_DIR/deployment-info.txt" <<EOF
Deployment Date: $(date)
Server IP: $(hostname -I | awk '{print $1}')
Docker Version: $(docker --version)
Docker Compose Version: $(docker compose version)
Project Directory: $PROJECT_DIR
EOF
    
    print_success "Deployment information saved to $PROJECT_DIR/deployment-info.txt"
}

# Run main function
main "$@"
