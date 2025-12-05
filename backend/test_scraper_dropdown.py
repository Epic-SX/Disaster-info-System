#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for the modified JMA AMeDAS scraper using dropdown approach
"""

import asyncio
import logging
import json
from jma_amedas_scraper import JMAAMeDASSeleniumScraper

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_single_prefecture():
    """Test scraping a single prefecture"""
    print("=" * 80)
    print("Testing Modified JMA AMeDAS Scraper - Dropdown Approach")
    print("=" * 80)
    
    scraper = JMAAMeDASSeleniumScraper(headless=True)
    
    # Test scraping 青森県 (020000)
    print("\nTest 1: Scraping 青森県 (020000)...")
    print("-" * 80)
    
    aomori_data = scraper.scrape_prefecture("020000")
    
    if aomori_data:
        print(f"\n✓ Successfully scraped {len(aomori_data)} regions")
        
        total_observations = sum(len(region['observations']) for region in aomori_data)
        print(f"✓ Total observations: {total_observations}")
        
        # Display data for first region
        if aomori_data[0]['observations']:
            first_region = aomori_data[0]
            print(f"\n{'='*80}")
            print(f"Region: {first_region['region_name']}")
            print(f"Prefecture: {first_region.get('prefecture_name', 'N/A')}")
            print(f"Observation Time: {first_region['observation_time']}")
            print(f"Total Stations: {len(first_region['observations'])}")
            print(f"{'='*80}\n")
            
            print(f"{'Station ID':<12} {'Location':<20} {'Temp(°C)':<10} {'Precip(mm)':<12}")
            print("-" * 60)
            
            for obs in first_region['observations'][:10]:  # Show first 10 observations
                print(f"{obs['location_id']:<12} {obs['location_name']:<20} "
                      f"{obs['temperature']:<10} {obs['precipitation_1h']:<12}")
        
    else:
        print("✗ Failed to scrape 青森県 data")
    
    print("\n" + "=" * 80)
    print("Test completed!")


def test_multiple_prefectures():
    """Test scraping multiple prefectures using the dropdown"""
    print("=" * 80)
    print("Testing Modified JMA AMeDAS Scraper - Multiple Prefectures")
    print("=" * 80)
    
    scraper = JMAAMeDASSeleniumScraper(headless=True)
    
    # Test prefectures
    test_prefectures = [
        ("010000", "北海道"),
        ("020000", "青森県"),
        ("130000", "東京都"),
    ]
    
    all_data = []
    
    # Setup driver once
    scraper._setup_driver()
    
    # Navigate to base page once
    if not scraper._navigate_to_base_page():
        print("✗ Failed to navigate to base page")
        return
    
    print("✓ Base page loaded\n")
    
    for code, name in test_prefectures:
        print(f"Scraping {name} ({code})...")
        
        # Select prefecture from dropdown
        if not scraper._select_prefecture_from_dropdown(code):
            print(f"✗ Failed to select {name}")
            continue
        
        # Wait for data
        import time
        time.sleep(5)
        
        # Get and parse data
        html_content = scraper.driver.page_source
        regions_data = scraper._parse_table_data(html_content)
        
        # Add prefecture info
        for region in regions_data:
            region['prefecture_code'] = code
            region['prefecture_name'] = name
        
        if regions_data:
            all_data.extend(regions_data)
            print(f"✓ {name}: scraped {len(regions_data)} regions")
        else:
            print(f"✗ {name}: no data")
        
        print()
    
    # Close driver
    scraper._close_driver()
    
    # Summary
    total_observations = sum(len(region['observations']) for region in all_data)
    print("=" * 80)
    print(f"Summary: {len(all_data)} regions, {total_observations} observations")
    print("=" * 80)
    
    # Export to JSON
    output_file = "test_scraper_result.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    print(f"✓ Data exported to: {output_file}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--multi':
        test_multiple_prefectures()
    else:
        test_single_prefecture()


