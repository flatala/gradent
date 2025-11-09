#!/usr/bin/env bash
# Quick setup script - run this to set up your development environment

echo "🚀 Gradent Study Assistant - Quick Setup"
echo ""

# Check if Python is available
if ! command -v python &> /dev/null; then
    echo "❌ Python not found. Please install Python 3.12+ first."
    exit 1
fi

# Check if poetry is available
if ! command -v poetry &> /dev/null; then
    echo "❌ Poetry not found. Please install Poetry first."
    echo "   Visit: https://python-poetry.org/docs/#installation"
    exit 1
fi

echo "✓ Python found: $(python --version)"
echo "✓ Poetry found: $(poetry --version)"
echo ""

# Install dependencies
echo "📦 Installing dependencies..."
poetry install
if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies"
    exit 1
fi
echo "✓ Dependencies installed"
echo ""

# Run setup script
echo "🔧 Setting up databases and mock data..."
poetry run python scripts/setup_all.py "$@"
exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo ""
    echo "🎉 Setup complete! You're ready to go."
    echo ""
    echo "To start the application:"
    echo "  poetry run python main.py"
    echo ""
    echo "To run tests:"
    echo "  poetry run pytest"
else
    echo ""
    echo "❌ Setup failed. Please check the errors above."
fi

exit $exit_code
