#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to verify the full scraping works for all regions
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


def test_all_regions():
    """Test scraping all regions"""
    print("=" * 80)
    print("JMA AMeDAS Scraper - Full Test (All Regions)")
    print("=" * 80)
    print("\nThis will scrape all 11 major regions in Japan")
    print("Expected regions:")
    print("  1. 北海道 (Hokkaido)")
    print("  2. 東北 (Tohoku)")
    print("  3. 関東甲信 (Kanto-Koshin)")
    print("  4. 北陸 (Hokuriku)")
    print("  5. 東海 (Tokai)")
    print("  6. 近畿 (Kinki)")
    print("  7. 中国（山口は除く） (Chugoku, excluding Yamaguchi)")
    print("  8. 四国 (Shikoku)")
    print("  9. 九州北部（山口を含む） (Northern Kyushu, including Yamaguchi)")
    print(" 10. 九州南部・奄美 (Southern Kyushu & Amami)")
    print(" 11. 沖縄 (Okinawa)")
    print("=" * 80)
    print()
    
    scraper = JMAAMeDASSeleniumScraper(headless=True)
    
    # Scrape all regions
    all_data = scraper.scrape_all_prefectures()
    
    if all_data:
        total_observations = sum(len(region['observations']) for region in all_data)
        print(f"\n{'='*80}")
        print(f"SUCCESS!")
        print(f"{'='*80}")
        print(f"Total sub-regions scraped: {len(all_data)}")
        print(f"Total observations: {total_observations}")
        
        # Group by major region
        region_summary = {}
        for region in all_data:
            major_region = region.get('major_region', 'Unknown')
            if major_region not in region_summary:
                region_summary[major_region] = {
                    'sub_regions': [],
                    'total_obs': 0
                }
            region_summary[major_region]['sub_regions'].append(region['region_name'])
            region_summary[major_region]['total_obs'] += len(region['observations'])
        
        print(f"\nBreakdown by major region:")
        print(f"{'='*80}")
        for major_region, data in sorted(region_summary.items()):
            print(f"\n{major_region}:")
            print(f"  Sub-regions: {', '.join(data['sub_regions'][:5])}")
            if len(data['sub_regions']) > 5:
                print(f"  ... and {len(data['sub_regions']) - 5} more")
            print(f"  Total observations: {data['total_obs']}")
        
        # Export to JSON
        print(f"\n{'='*80}")
        print("Exporting data to JSON...")
        output_file = "amedas_data.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
        print(f"✓ Data exported to: {output_file}")
        print(f"  File size: {len(json.dumps(all_data, ensure_ascii=False))} bytes")
        print(f"{'='*80}")
        
    else:
        print("\n✗ Failed to scrape data")
    
    print("\nTest completed!")


if __name__ == "__main__":
    test_all_regions()


