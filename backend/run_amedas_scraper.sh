#!/bin/bash
# Wrapper script for running AMeDAS scraper with logging

# Set working directory
cd /home/ubuntu/Disaster-info-System/backend

# Create logs directory if it doesn't exist
mkdir -p logs

# Log file with timestamp
LOG_FILE="logs/amedas_scraper_$(date +%Y%m%d).log"

# Log start time
echo "========================================" >> "$LOG_FILE"
echo "Starting AMeDAS scraper at $(date)" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"

# Run the scraper (using --api mode for JSON API, or remove --api for Selenium)
/usr/bin/python3 jma_amedas_scraper.py --api >> "$LOG_FILE" 2>&1

# Capture exit code
EXIT_CODE=$?

# Log completion
echo "----------------------------------------" >> "$LOG_FILE"
echo "Scraper finished at $(date) with exit code: $EXIT_CODE" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

# Keep only last 7 days of logs
find logs/ -name "amedas_scraper_*.log" -mtime +7 -delete

exit $EXIT_CODE
