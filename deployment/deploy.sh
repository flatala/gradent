#!/bin/bash

# Deployment script for Gradent Study Assistant
# This script automates the deployment process on Ubuntu VMs

set -e  # Exit on error

echo "=========================================="
echo "Gradent Deployment Script"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Check if running on Linux
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    print_error "This script is designed for Linux systems only."
    exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    echo "Run: curl -fsSL https://get.docker.com | sh"
    exit 1
fi

print_success "Docker is installed"

# Check if Docker Compose is installed
if ! command -v docker compose &> /dev/null; then
    print_error "Docker Compose is not installed."
    exit 1
fi

print_success "Docker Compose is installed"

# Check if .env file exists
if [ ! -f .env ]; then
    print_warning ".env file not found. Creating from .env.example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        print_warning "Please edit .env file with your configuration before proceeding."
        print_warning "At minimum, set your OPENAI_API_KEY"
        echo ""
        read -p "Press Enter after you've configured .env file..."
    else
        print_error ".env.example not found. Cannot create .env file."
        exit 1
    fi
fi

# Check if OPENAI_API_KEY is set
if grep -q "OPENAI_API_KEY=sk-your-api-key-here" .env || ! grep -q "OPENAI_API_KEY=sk-" .env; then
    print_error "OPENAI_API_KEY is not configured in .env file"
    print_warning "Please set a valid OpenAI API key in .env file"
    exit 1
fi

print_success ".env file is configured"

# Create necessary directories
echo ""
echo "Creating necessary directories..."
mkdir -p data logs uploads data/vector_db
print_success "Directories created"

# Stop existing containers if running
echo ""
echo "Stopping existing containers (if any)..."
docker compose down 2>/dev/null || true

# Build and start containers
echo ""
echo "Building Docker images (this may take a few minutes)..."
docker compose build

print_success "Docker images built successfully"

echo ""
echo "Starting containers..."
docker compose up -d

# Wait for containers to be healthy
echo ""
echo "Waiting for containers to be healthy..."
sleep 5

# Check backend health
echo "Checking backend health..."
for i in {1..30}; do
    if curl -f http://localhost:8000/health &> /dev/null; then
        print_success "Backend is healthy"
        break
    fi
    if [ $i -eq 30 ]; then
        print_error "Backend failed to start properly"
        echo "Check logs with: docker compose logs backend"
        exit 1
    fi
    sleep 2
done

# Check frontend health
echo "Checking frontend health..."
for i in {1..30}; do
    if curl -f http://localhost/ &> /dev/null; then
        print_success "Frontend is healthy"
        break
    fi
    if [ $i -eq 30 ]; then
        print_error "Frontend failed to start properly"
        echo "Check logs with: docker compose logs frontend"
        exit 1
    fi
    sleep 2
done

# Initialize database
echo ""
read -p "Do you want to initialize the database with mock data? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Initializing database..."
    docker compose exec backend python scripts/setup_all.py
    print_success "Database initialized"
fi

# Show status
echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo ""
docker compose ps
echo ""
echo "Access the application:"
echo "  Frontend: http://localhost/ or http://$(hostname -I | awk '{print $1}')/"
echo "  Backend:  http://localhost:8000 or http://$(hostname -I | awk '{print $1}'):8000"
echo "  API Docs: http://localhost:8000/docs"
echo ""
echo "Useful commands:"
echo "  View logs:        docker compose logs -f"
echo "  Stop services:    docker compose down"
echo "  Restart services: docker compose restart"
echo "  Check status:     docker compose ps"
echo ""
print_success "Deployment successful! 🎉"
