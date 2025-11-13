#!/bin/bash
# Setup cron job for AMeDAS scraper

echo "Setting up AMeDAS scraper cron job..."
echo "This will run the scraper every hour to update amedas_data.json"
echo ""

# Define the cron job
CRON_JOB="0 * * * * /home/ubuntu/Disaster-info-System/backend/run_amedas_scraper.sh"

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "run_amedas_scraper.sh"; then
    echo "⚠️  Cron job already exists. Current crontab:"
    echo ""
    crontab -l | grep "run_amedas_scraper.sh"
    echo ""
    read -p "Do you want to update it? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Cancelled."
        exit 0
    fi
    # Remove old cron job
    crontab -l | grep -v "run_amedas_scraper.sh" | crontab -
fi

# Add new cron job
(crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -

echo ""
echo "✓ Cron job installed successfully!"
echo ""
echo "Schedule: Every hour at minute 0 (e.g., 1:00, 2:00, 3:00...)"
echo "Script: /home/ubuntu/Disaster-info-System/backend/run_amedas_scraper.sh"
echo "Output: amedas_data.json"
echo "Logs: logs/amedas_scraper_YYYYMMDD_HHMMSS.log"
echo ""
echo "Current crontab:"
crontab -l
echo ""
echo "To view logs: ls -lh /home/ubuntu/Disaster-info-System/backend/logs/"
echo "To remove cron job: crontab -e (then delete the line)"
echo "To test manually: /home/ubuntu/Disaster-info-System/backend/run_amedas_scraper.sh"

