#!/bin/bash
# Script to install Chromium browser for Selenium scraping

echo "Installing Chromium browser..."
sudo apt-get update
sudo apt-get install -y chromium-browser

echo ""
echo "Installation complete!"
echo "Chrome/Chromium version:"
chromium-browser --version || google-chrome --version

echo ""
echo "Now you can run the scraper with:"
echo "  cd /home/ubuntu/Disaster-info-System/backend"
echo "  source venv/bin/activate"
echo "  python3 jma_amedas_scraper.py"

