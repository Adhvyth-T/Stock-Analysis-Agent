#!/bin/bash

# ==============================================
# Stock Analysis Bot - Setup Script
# ==============================================

set -e  # Exit on error

echo "=========================================="
echo "Stock Analysis Bot - Setup"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Python version
echo -e "${YELLOW}Checking Python version...${NC}"
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
    echo -e "${GREEN}Virtual environment created${NC}"
else
    echo -e "${GREEN}Virtual environment already exists${NC}"
fi

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source venv/bin/activate

# Upgrade pip
echo -e "${YELLOW}Upgrading pip...${NC}"
pip install --upgrade pip

# Install dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
pip install -r requirements.txt

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Creating .env from template...${NC}"
    cp .env.example .env
    echo -e "${RED}IMPORTANT: Please edit .env and add your API keys!${NC}"
else
    echo -e "${GREEN}.env file already exists${NC}"
fi

# Initialize database
echo -e "${YELLOW}Initializing database...${NC}"
python scripts/setup_db.py

# Run tests (optional)
read -p "Run tests? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Running tests...${NC}"
    pytest tests/ -v --tb=short
fi

echo ""
echo "=========================================="
echo -e "${GREEN}Setup complete!${NC}"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Edit .env file with your API keys"
echo "2. Run the bot: python main.py"
echo ""
echo "Commands:"
echo "  source venv/bin/activate  # Activate venv"
echo "  python main.py            # Run bot"
echo "  pytest tests/ -v          # Run tests"
echo ""
