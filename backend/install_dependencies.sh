#!/bin/bash
# Installation script for JMA AMeDAS Scraper dependencies

set -e

echo "=========================================="
echo "Installing Dependencies for AMeDAS Scraper"
echo "=========================================="

# Update pip, setuptools, and wheel first (critical for Python 3.12)
echo ""
echo "Step 1: Updating pip, setuptools, and wheel..."
pip install --upgrade pip setuptools wheel

# Install Chrome and ChromeDriver (required for Selenium)
echo ""
echo "Step 2: Installing Chrome and ChromeDriver..."
if command -v google-chrome &> /dev/null; then
    echo "✓ Google Chrome is already installed"
else
    echo "Installing Chromium browser and chromedriver..."
    sudo apt-get update
    sudo apt-get install -y chromium-browser chromium-chromedriver
    
    # Create symlink if needed
    if [ ! -f /usr/bin/chromedriver ]; then
        if [ -f /usr/lib/chromium-browser/chromedriver ]; then
            sudo ln -s /usr/lib/chromium-browser/chromedriver /usr/bin/chromedriver
        fi
    fi
fi

# Verify ChromeDriver installation
if command -v chromedriver &> /dev/null; then
    echo "✓ ChromeDriver is installed: $(chromedriver --version)"
else
    echo "⚠ Warning: ChromeDriver not found in PATH"
fi

# Install Python dependencies
echo ""
echo "Step 3: Installing Python packages from requirements.txt..."
pip install -r requirements.txt

echo ""
echo "=========================================="
echo "✓ Installation completed successfully!"
echo "=========================================="
echo ""
echo "You can now test the scraper with:"
echo "  python jma_amedas_scraper.py --selenium"
echo ""

