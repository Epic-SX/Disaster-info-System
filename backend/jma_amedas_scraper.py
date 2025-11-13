#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JMA AMeDAS Table Data Scraper
Scrapes weather observation data from JMA AMeDAS website using Selenium
https://www.jma.go.jp/bosai/amedas/
"""

import asyncio
import aiohttp
import logging
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import re

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class AMeDASObservation:
    """Single AMeDAS observation data point"""
    location_name: str
    location_id: str
    temperature: Optional[str] = None  # °C
    precipitation_1h: Optional[str] = None  # mm
    wind_direction: Optional[str] = None  # 16方位
    wind_speed: Optional[str] = None  # m/s
    sunshine_duration_1h: Optional[str] = None  # h
    snow_depth: Optional[str] = None  # cm
    humidity: Optional[str] = None  # %
    local_pressure: Optional[str] = None  # hPa
    sea_level_pressure: Optional[str] = None  # hPa
    observation_time: Optional[str] = None
    region_name: Optional[str] = None


@dataclass
class AMeDASRegionData:
    """AMeDAS data for a region"""
    region_name: str
    region_code: str
    observation_time: str
    observations: List[AMeDASObservation]


class JMAAMeDASSeleniumScraper:
    """Selenium-based scraper for JMA AMeDAS table data"""
    
    def __init__(self, headless: bool = True):
        """
        Initialize the Selenium scraper
        
        Args:
            headless: Run browser in headless mode (default: True)
        """
        self.base_url = "https://www.jma.go.jp/bosai/amedas/"
        self.headless = headless
        self.driver = None
        
        # Prefecture codes and names mapping
        self.prefecture_mapping = {
            "010000": "北海道",
            "020000": "青森県",
            "030000": "岩手県",
            "040000": "宮城県",
            "050000": "秋田県",
            "060000": "山形県",
            "070000": "福島県",
            "080000": "茨城県",
            "090000": "栃木県",
            "100000": "群馬県",
            "110000": "埼玉県",
            "120000": "千葉県",
            "130000": "東京都",
            "140000": "神奈川県",
            "150000": "新潟県",
            "160000": "富山県",
            "170000": "石川県",
            "180000": "福井県",
            "190000": "山梨県",
            "200000": "長野県",
            "210000": "岐阜県",
            "220000": "静岡県",
            "230000": "愛知県",
            "240000": "三重県",
            "250000": "滋賀県",
            "260000": "京都府",
            "270000": "大阪府",
            "280000": "兵庫県",
            "290000": "奈良県",
            "300000": "和歌山県",
            "310000": "鳥取県",
            "320000": "島根県",
            "330000": "岡山県",
            "340000": "広島県",
            "350000": "山口県",
            "360000": "徳島県",
            "370000": "香川県",
            "380000": "愛媛県",
            "390000": "高知県",
            "400000": "福岡県",
            "410000": "佐賀県",
            "420000": "長崎県",
            "430000": "熊本県",
            "440000": "大分県",
            "450000": "宮崎県",
            "460000": "鹿児島県",
            "471000": "沖縄県",
        }
        
        # Map prefecture codes to their parent regions (as shown in the dropdown)
        self.prefecture_to_region = {
            "010000": "北海道",  # Hokkaido
            "020000": "東北",    # Tohoku - Aomori
            "030000": "東北",    # Tohoku - Iwate
            "040000": "東北",    # Tohoku - Miyagi
            "050000": "東北",    # Tohoku - Akita
            "060000": "東北",    # Tohoku - Yamagata
            "070000": "東北",    # Tohoku - Fukushima
            "080000": "関東甲信",  # Kanto-Koshin - Ibaraki
            "090000": "関東甲信",  # Kanto-Koshin - Tochigi
            "100000": "関東甲信",  # Kanto-Koshin - Gunma
            "110000": "関東甲信",  # Kanto-Koshin - Saitama
            "120000": "関東甲信",  # Kanto-Koshin - Chiba
            "130000": "関東甲信",  # Kanto-Koshin - Tokyo
            "140000": "関東甲信",  # Kanto-Koshin - Kanagawa
            "150000": "関東甲信",  # Kanto-Koshin - Niigata (also sometimes in Hokuriku)
            "160000": "北陸",    # Hokuriku - Toyama
            "170000": "北陸",    # Hokuriku - Ishikawa
            "180000": "北陸",    # Hokuriku - Fukui
            "190000": "関東甲信",  # Kanto-Koshin - Yamanashi
            "200000": "関東甲信",  # Kanto-Koshin - Nagano
            "210000": "東海",    # Tokai - Gifu
            "220000": "東海",    # Tokai - Shizuoka
            "230000": "東海",    # Tokai - Aichi
            "240000": "東海",    # Tokai - Mie
            "250000": "近畿",    # Kinki - Shiga
            "260000": "近畿",    # Kinki - Kyoto
            "270000": "近畿",    # Kinki - Osaka
            "280000": "近畿",    # Kinki - Hyogo
            "290000": "近畿",    # Kinki - Nara
            "300000": "近畿",    # Kinki - Wakayama
            "310000": "中国（山口は除く）",  # Chugoku - Tottori
            "320000": "中国（山口は除く）",  # Chugoku - Shimane
            "330000": "中国（山口は除く）",  # Chugoku - Okayama
            "340000": "中国（山口は除く）",  # Chugoku - Hiroshima
            "350000": "九州北部（山口を含む）",  # Northern Kyushu - Yamaguchi
            "360000": "四国",    # Shikoku - Tokushima
            "370000": "四国",    # Shikoku - Kagawa
            "380000": "四国",    # Shikoku - Ehime
            "390000": "四国",    # Shikoku - Kochi
            "400000": "九州北部（山口を含む）",  # Northern Kyushu - Fukuoka
            "410000": "九州北部（山口を含む）",  # Northern Kyushu - Saga
            "420000": "九州北部（山口を含む）",  # Northern Kyushu - Nagasaki
            "430000": "九州北部（山口を含む）",  # Northern Kyushu - Kumamoto
            "440000": "九州北部（山口を含む）",  # Northern Kyushu - Oita
            "450000": "九州南部・奄美",  # Southern Kyushu - Miyazaki
            "460000": "九州南部・奄美",  # Southern Kyushu - Kagoshima
            "471000": "沖縄",    # Okinawa
        }
    
    def _setup_driver(self):
        """Setup Chrome WebDriver with options"""
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument('--headless=new')  # Use new headless mode
        
        # Essential options for running in server environments
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-software-rasterizer')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-setuid-sandbox')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        
        # Use a random port to avoid conflicts
        import random
        debug_port = random.randint(9000, 9999)
        chrome_options.add_argument(f'--remote-debugging-port={debug_port}')
        
        # Memory and stability options
        chrome_options.add_argument('--disable-background-networking')
        chrome_options.add_argument('--disable-default-apps')
        chrome_options.add_argument('--disable-sync')
        chrome_options.add_argument('--metrics-recording-only')
        chrome_options.add_argument('--mute-audio')
        chrome_options.add_argument('--no-first-run')
        chrome_options.add_argument('--safebrowsing-disable-auto-update')
        chrome_options.add_argument('--disable-features=VizDisplayCompositor')
        chrome_options.add_argument('--disable-features=IsolateOrigins,site-per-process')
        chrome_options.add_argument('--js-flags=--max-old-space-size=512')  # Limit memory
        
        # Prevent crashes
        chrome_options.add_argument('--disable-crash-reporter')
        chrome_options.add_argument('--disable-in-process-stack-traces')
        chrome_options.add_argument('--disable-logging')
        chrome_options.add_argument('--log-level=3')
        chrome_options.add_argument('--silent')
        
        # Page load strategy
        chrome_options.page_load_strategy = 'normal'  # Wait for full page load
        
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Set user agent
        chrome_options.add_argument('user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Set Chrome binary location if using snap
        chrome_options.binary_location = "/snap/bin/chromium"
        
        # Use webdriver-manager to automatically manage ChromeDriver
        # Let it auto-detect the Chrome version and download matching driver
        from webdriver_manager.core.os_manager import ChromeType
        service = Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install())
        
        # Set service log path to suppress output
        service.log_path = '/dev/null'
        
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver.implicitly_wait(10)
        
        # Set page load timeout
        self.driver.set_page_load_timeout(60)
        self.driver.set_script_timeout(30)
        
        logger.info(f"Chrome WebDriver initialized (debug port: {debug_port})")
    
    def _close_driver(self):
        """Close the WebDriver safely"""
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                logger.warning(f"Error while closing driver: {e}")
                try:
                    # Force kill if quit failed
                    self.driver.service.process.kill()
                except:
                    pass
            finally:
                self.driver = None
                logger.info("Chrome WebDriver closed")
    
    def _navigate_to_base_page(self) -> bool:
        """
        Navigate to the base AMeDAS page
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Navigate to base URL (use Hokkaido as default)
            url = f"{self.base_url}#area_type=japan&area_code=010000"
            logger.info(f"Navigating to: {url}")
            
            self.driver.get(url)
            time.sleep(3)  # Wait for page to load and JavaScript to execute
            
            return True
            
        except Exception as e:
            logger.error(f"Error navigating to base page: {e}")
            return False
    
    def _select_prefecture_from_dropdown(self, prefecture_code: str) -> bool:
        """
        Select a prefecture from the dropdown menu
        
        Args:
            prefecture_code: Prefecture code (e.g., "010000" for Hokkaido)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            wait = WebDriverWait(self.driver, 20)
            prefecture_name = self.prefecture_mapping.get(prefecture_code, "")
            region_name = self.prefecture_to_region.get(prefecture_code, "")
            
            if not prefecture_name:
                logger.error(f"Unknown prefecture code: {prefecture_code}")
                return False
            
            if not region_name:
                logger.error(f"No region mapping for prefecture code: {prefecture_code}")
                return False
            
            logger.info(f"Searching for prefecture: {prefecture_name} (in region: {region_name})")
            
            # Wait for page to be ready
            time.sleep(2)
            wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
            
            # First, try to open the dropdown menu if it's not already open
            try:
                # Look for the dropdown button (id="menu_office")
                dropdown_button = self.driver.find_element(By.ID, "menu_office")
                
                # Check if dropdown is expanded
                aria_expanded = dropdown_button.get_attribute("aria-expanded")
                if aria_expanded != "true":
                    logger.info("Opening dropdown menu...")
                    self.driver.execute_script("arguments[0].click();", dropdown_button)
                    time.sleep(1)
                    logger.info("✓ Dropdown menu opened")
            except NoSuchElementException:
                logger.info("Dropdown button not found or not needed, proceeding...")
            except Exception as e:
                logger.warning(f"Could not open dropdown (may already be open): {e}")
            
            # Find the dropdown button (with id="menu_office" or class containing dropdown)
            # Try to find the area-center-link with the matching value attribute
            try:
                # Look for all area-center-link elements (全域 buttons)
                all_zeni_links = self.driver.find_elements(By.CLASS_NAME, "area-center-link")
                logger.info(f"Found {len(all_zeni_links)} 全域 buttons in dropdown")
                
                # Debug: Log all available options
                all_options = []
                for i, link in enumerate(all_zeni_links):
                    try:
                        value_attr = link.get_attribute("value")
                        parent_li = link.find_element(By.XPATH, "./..")
                        prefecture_link = parent_li.find_element(By.TAG_NAME, "a")
                        text_content = prefecture_link.text.strip()
                        all_options.append(f"{text_content} (value={value_attr})")
                        
                        if i < 5:  # Log first 5 for debugging
                            logger.info(f"  Option {i+1}: {text_content} (value={value_attr})")
                    except Exception as e:
                        logger.debug(f"  Could not parse option {i+1}: {e}")
                
                # Find the one matching our region name
                target_link = None
                for link in all_zeni_links:
                    try:
                        value_attr = link.get_attribute("value")
                        if value_attr:
                            parent_li = link.find_element(By.XPATH, "./..")
                            region_link = parent_li.find_element(By.TAG_NAME, "a")
                            text_content = region_link.text.strip()
                            
                            # Check for exact match first, then substring match with region name
                            if text_content == region_name or region_name in text_content:
                                target_link = link
                                logger.info(f"✓ Found matching 全域 button for region '{region_name}' (prefecture: {prefecture_name}, value={value_attr})")
                                break
                    except Exception as e:
                        logger.debug(f"Error checking link: {e}")
                        continue
                
                if not target_link:
                    logger.error(f"Could not find 全域 button for region '{region_name}' (prefecture: {prefecture_name})")
                    logger.info(f"Available options: {', '.join(all_options[:10])}...")  # Show first 10
                    return False
                
                # Scroll into view and click
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'instant', block: 'center'});", target_link)
                time.sleep(1)
                
                # Click using JavaScript
                self.driver.execute_script("arguments[0].click();", target_link)
                logger.info(f"✓ Clicked 全域 button for region {region_name} (prefecture: {prefecture_name})")
                
                # Wait for data to load
                time.sleep(5)
                
                # Verify that tables are loading
                tables = self.driver.find_elements(By.CLASS_NAME, "contents-block")
                logger.info(f"Found {len(tables)} content blocks after clicking")
                
                return True
                
            except Exception as e:
                logger.error(f"Error finding/clicking 全域 button: {e}")
                return False
            
        except Exception as e:
            logger.error(f"Error selecting prefecture from dropdown: {e}")
            return False
    
    
    def _parse_table_data(self, html_content: str) -> List[Dict[str, Any]]:
        """
        Parse the AMeDAS table data from HTML
        
        Args:
            html_content: HTML content of the page
            
        Returns:
            List of region data dictionaries
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        regions_data = []
        
        try:
            # Find all region sections (each has a title table and a data table)
            # Look for divs with class "contents-block" that contain tables
            blocks = soup.find_all('div', class_='contents-block')
            logger.info(f"Found {len(blocks)} data blocks")
            
            for block in blocks:
                # Get region name from the title row in the first table
                title_row = block.find('tr', class_='contents-title')
                if not title_row:
                    continue
                
                region_name = title_row.find('th').get_text(strip=True)
                # Remove "の観測データ" suffix if present
                region_name = region_name.replace('の観測データ', '')
                
                # Get observation time
                obs_time_element = block.find('span', class_='amd-areastable-span-obstime')
                obs_time = obs_time_element.get_text(strip=True) if obs_time_element else ""
                
                # Find all data rows - they're in the second table inside contents-wide-table-body
                data_rows = block.find_all('tr', class_='amd-areastable-tr-pointdata')
                logger.info(f"Region: {region_name}, Data rows: {len(data_rows)}")
                
                observations = []
                
                for row in data_rows:
                    try:
                        # Extract location name and ID from the first cell
                        location_cell = row.find('a', class_='amd-areastable-a-pointlink')
                        if not location_cell:
                            continue
                        
                        location_name = location_cell.get_text(strip=True)
                        location_href = location_cell.get('href', '')
                        # Extract station ID from href like "#amdno=11001"
                        location_id_match = re.search(r'amdno=(\d+)', location_href)
                        location_id = location_id_match.group(1) if location_id_match else ""
                        
                        # Extract data using class names
                        def get_cell_by_class(class_name, default="---"):
                            cell = row.find('td', class_=class_name)
                            if cell:
                                value = cell.get_text(strip=True)
                                return value if value else default
                            return default
                        
                        observation = AMeDASObservation(
                            location_name=location_name,
                            location_id=location_id,
                            temperature=get_cell_by_class('td-temp'),
                            precipitation_1h=get_cell_by_class('td-precipitation1h'),
                            wind_direction=get_cell_by_class('td-windDirection'),
                            wind_speed=get_cell_by_class('td-wind'),
                            sunshine_duration_1h=get_cell_by_class('td-sun1h'),
                            snow_depth=get_cell_by_class('td-snow'),
                            humidity=get_cell_by_class('td-humidity'),
                            local_pressure=get_cell_by_class('td-pressure'),
                            sea_level_pressure=get_cell_by_class('td-normalPressure'),
                            observation_time=obs_time,
                            region_name=region_name
                        )
                        
                        observations.append(observation)
                        
                    except Exception as e:
                        logger.warning(f"Error parsing row: {e}")
                        continue
                
                if observations:
                    region_data = {
                        "region_name": region_name,
                        "region_code": "",  # Will be filled later if needed
                        "observation_time": obs_time,
                        "observations": [asdict(obs) for obs in observations]
                    }
                    regions_data.append(region_data)
            
            logger.info(f"Parsed {len(regions_data)} regions with total {sum(len(r['observations']) for r in regions_data)} observations")
            
        except Exception as e:
            logger.error(f"Error parsing table data: {e}")
        
        return regions_data
    
    def scrape_prefecture(self, prefecture_code: str, driver_initialized: bool = False, max_retries: int = 3) -> List[Dict[str, Any]]:
        """
        Scrape AMeDAS data for a specific prefecture with retry logic
        
        Args:
            prefecture_code: Prefecture code (e.g., "010000" for Hokkaido)
            driver_initialized: If True, assumes driver is already initialized and page is loaded
            max_retries: Maximum number of retry attempts (default: 3)
            
        Returns:
            List of region data dictionaries
        """
        for attempt in range(max_retries):
            driver_closed = False
            try:
                if attempt > 0:
                    logger.info(f"Retry attempt {attempt + 1}/{max_retries} for {prefecture_code}")
                    time.sleep(3 * attempt)  # Exponential backoff
                
                # Setup driver if not already initialized
                if not driver_initialized:
                    self._setup_driver()
                    
                    # Navigate to base page
                    if not self._navigate_to_base_page():
                        logger.error("Failed to navigate to base page")
                        if not driver_initialized:
                            self._close_driver()
                            driver_closed = True
                        continue
                
                # Select prefecture from dropdown and click its 全域 button
                if not self._select_prefecture_from_dropdown(prefecture_code):
                    logger.error(f"Failed to select prefecture {prefecture_code} from dropdown")
                    if not driver_initialized:
                        self._close_driver()
                        driver_closed = True
                    continue
                
                # Wait for data to load (longer wait for tables to populate)
                logger.info("Waiting for data tables to populate...")
                time.sleep(5)
                
                # Verify driver is still alive before accessing page source
                try:
                    # Try to get current URL to verify connection
                    _ = self.driver.current_url
                    logger.info("✓ Driver connection verified")
                except Exception as verify_error:
                    logger.error(f"Driver connection lost: {verify_error}")
                    if not driver_initialized:
                        self._close_driver()
                        driver_closed = True
                    continue
                
                # Get page source with error handling
                try:
                    html_content = self.driver.page_source
                    logger.info(f"✓ Page source retrieved ({len(html_content)} bytes)")
                except Exception as page_error:
                    logger.error(f"Failed to get page source: {page_error}")
                    if not driver_initialized:
                        self._close_driver()
                        driver_closed = True
                    continue
                
                # Parse table data
                regions_data = self._parse_table_data(html_content)
                
                # Add prefecture code to regions
                for region in regions_data:
                    region['prefecture_code'] = prefecture_code
                    region['prefecture_name'] = self.prefecture_mapping.get(prefecture_code, "")
                
                if regions_data:
                    logger.info(f"✓ Successfully scraped {len(regions_data)} regions for {prefecture_code}")
                    if not driver_initialized:
                        self._close_driver()
                        driver_closed = True
                    return regions_data
                else:
                    logger.warning(f"No data found for {prefecture_code}, attempt {attempt + 1}")
                    if not driver_initialized:
                        self._close_driver()
                        driver_closed = True
                    continue
                
            except Exception as e:
                logger.error(f"Error scraping prefecture data (attempt {attempt + 1}/{max_retries}): {e}")
                if not driver_closed and not driver_initialized:
                    self._close_driver()
                if attempt < max_retries - 1:
                    continue
            
            finally:
                if not driver_closed and not driver_initialized and self.driver is not None:
                    self._close_driver()
        
        logger.error(f"Failed to scrape {prefecture_code} after {max_retries} attempts")
        return []
    
    def scrape_all_prefectures(self) -> List[Dict[str, Any]]:
        """
        Scrape AMeDAS data for all prefectures with progress tracking
        Uses a single browser session and scrapes by region (more efficient)
        
        Returns:
            List of all region data dictionaries
        """
        all_data = []
        failed_regions = []
        
        # Group prefectures by region to avoid duplicate scraping
        region_to_prefectures = {}
        for pref_code, pref_name in self.prefecture_mapping.items():
            region = self.prefecture_to_region.get(pref_code)
            if region:
                if region not in region_to_prefectures:
                    region_to_prefectures[region] = []
                region_to_prefectures[region].append((pref_code, pref_name))
        
        unique_regions = list(region_to_prefectures.keys())
        total_regions = len(unique_regions)
        
        logger.info(f"Scraping {total_regions} unique regions covering {len(self.prefecture_mapping)} prefectures")
        
        try:
            # Setup driver once for all regions
            self._setup_driver()
            
            # Navigate to base page once
            if not self._navigate_to_base_page():
                logger.error("Failed to navigate to base page")
                return []
            
            logger.info("✓ Base page loaded, starting to scrape all regions...")
            
            for idx, region_name in enumerate(unique_regions, 1):
                prefectures_in_region = region_to_prefectures[region_name]
                pref_names = ", ".join([name for _, name in prefectures_in_region])
                
                logger.info(f"[{idx}/{total_regions}] Scraping region: {region_name}")
                logger.info(f"  Prefectures: {pref_names}")
                
                try:
                    # Use the first prefecture code from this region to trigger the dropdown
                    first_pref_code = prefectures_in_region[0][0]
                    
                    # Select region from dropdown
                    if not self._select_prefecture_from_dropdown(first_pref_code):
                        logger.error(f"Failed to select region {region_name} from dropdown")
                        failed_regions.append(region_name)
                        time.sleep(2)
                        continue
                    
                    # Wait for data to load
                    logger.info("Waiting for data tables to populate...")
                    time.sleep(5)
                    
                    # Get page source
                    try:
                        html_content = self.driver.page_source
                        logger.info(f"✓ Page source retrieved ({len(html_content)} bytes)")
                    except Exception as page_error:
                        logger.error(f"Failed to get page source: {page_error}")
                        failed_regions.append(region_name)
                        continue
                    
                    # Parse table data
                    regions_data = self._parse_table_data(html_content)
                    
                    # Note: The scraped data contains sub-regions, not prefectures
                    # We'll mark all with the region name for now
                    for region in regions_data:
                        region['major_region'] = region_name
                        # We can't easily map sub-regions to prefectures without additional data
                        # So we'll leave prefecture_code and prefecture_name empty for now
                        region['prefecture_code'] = ""
                        region['prefecture_name'] = ""
                    
                    if regions_data:
                        all_data.extend(regions_data)
                        logger.info(f"✓ [{idx}/{total_regions}] {region_name} completed - {len(regions_data)} sub-regions")
                    else:
                        failed_regions.append(region_name)
                        logger.warning(f"✗ [{idx}/{total_regions}] {region_name} failed - no data")
                    
                    # Brief pause between regions
                    time.sleep(2)
                    
                except Exception as e:
                    logger.error(f"✗ [{idx}/{total_regions}] Error scraping {region_name}: {e}")
                    failed_regions.append(region_name)
                    time.sleep(2)
                    continue
            
        except Exception as e:
            logger.error(f"Critical error during scraping: {e}")
        
        finally:
            # Close driver after all regions
            self._close_driver()
        
        total_observations = sum(len(region['observations']) for region in all_data)
        
        logger.info(f"\n{'='*80}")
        logger.info(f"Scraping Summary:")
        logger.info(f"  Completed: {total_regions - len(failed_regions)}/{total_regions} regions")
        logger.info(f"  Total sub-regions: {len(all_data)}")
        logger.info(f"  Total observations: {total_observations}")
        
        if failed_regions:
            logger.warning(f"  Failed regions ({len(failed_regions)}):")
            for region in failed_regions:
                logger.warning(f"    - {region}")
        
        logger.info(f"{'='*80}\n")
        
        return all_data


class JMAAMeDASAPI:
    """Direct API access to JMA AMeDAS JSON data"""
    
    def __init__(self):
        self.base_url = "https://www.jma.go.jp/bosai/amedas"
        self.latest_time_url = f"{self.base_url}/data/latest_time.txt"
        self.map_data_url = f"{self.base_url}/data/map"
        self.point_data_url = f"{self.base_url}/data/point"
        self.table_url = f"{self.base_url}/const/amedastable.json"
        
        # Region codes mapping (based on station ID prefixes)
        # Station IDs use 2-digit prefixes: 11=Hokkaido, 31-46=Tohoku/Kanto, etc.
        self.region_codes = {
            "11": "北海道 - 宗谷地方",
            "12": "北海道 - 上川留萌地方",
            "13": "北海道 - 網走北見紋別地方",
            "14": "北海道 - 十勝地方",
            "15": "北海道 - 釧路根室地方",
            "16": "北海道 - 胆振日高地方",
            "17": "北海道 - 石狩空知後志地方",
            "18": "北海道 - 渡島檜山地方",
            "19": "東北 - 青森県",
            "20": "東北 - 岩手県",
            "21": "東北 - 宮城県",
            "22": "東北 - 秋田県",
            "23": "東北 - 山形県",
            "24": "東北 - 福島県",
            "31": "関東 - 茨城県",
            "32": "関東 - 栃木県",
            "33": "関東 - 群馬県",
            "34": "関東 - 埼玉県",
            "35": "関東 - 千葉県",
            "36": "関東 - 東京都",
            "40": "関東 - 神奈川県",
            "41": "中部 - 山梨県",
            "42": "中部 - 長野県",
            "43": "中部 - 新潟県",
            "44": "中部 - 富山県",
            "45": "中部 - 石川県",
            "46": "中部 - 福井県",
            "48": "中部 - 岐阜県",
            "49": "中部 - 静岡県",
            "50": "中部 - 愛知県",
            "51": "中部 - 三重県",
            "52": "近畿 - 滋賀県",
            "53": "近畿 - 京都府",
            "54": "近畿 - 大阪府",
            "55": "近畿 - 兵庫県",
            "56": "近畿 - 奈良県",
            "57": "近畿 - 和歌山県",
            "60": "中国 - 鳥取県",
            "61": "中国 - 島根県",
            "62": "中国 - 岡山県",
            "63": "中国 - 広島県",
            "64": "中国 - 山口県",
            "65": "四国 - 徳島県",
            "66": "四国 - 香川県",
            "67": "四国 - 愛媛県",
            "68": "四国 - 高知県",
            "71": "九州 - 福岡県",
            "72": "九州 - 佐賀県",
            "73": "九州 - 長崎県",
            "74": "九州 - 熊本県",
            "81": "九州 - 大分県",
            "82": "九州 - 宮崎県",
            "83": "九州 - 鹿児島県",
            "84": "九州 - 奄美地方",
            "85": "沖縄 - 沖縄本島",
            "86": "沖縄 - 大東島",
            "87": "沖縄 - 宮古島",
            "88": "沖縄 - 八重山",
            "91": "小笠原",
            "92": "南大東",
            "93": "南鳥島",
            "94": "父島",
        }
        
        # Prefecture mapping for high-level grouping
        self.prefecture_codes = {
            "010000": ("北海道", ["11", "12", "13", "14", "15", "16", "17", "18"]),
            "020000": ("青森県", ["19"]),
            "030000": ("岩手県", ["20"]),
            "040000": ("宮城県", ["21"]),
            "050000": ("秋田県", ["22"]),
            "060000": ("山形県", ["23"]),
            "070000": ("福島県", ["24"]),
            "080000": ("茨城県", ["31"]),
            "090000": ("栃木県", ["32"]),
            "100000": ("群馬県", ["33"]),
            "110000": ("埼玉県", ["34"]),
            "120000": ("千葉県", ["35"]),
            "130000": ("東京都", ["36", "91", "94"]),
            "140000": ("神奈川県", ["40"]),
            "150000": ("新潟県", ["43"]),
            "160000": ("富山県", ["44"]),
            "170000": ("石川県", ["45"]),
            "180000": ("福井県", ["46"]),
            "190000": ("山梨県", ["41"]),
            "200000": ("長野県", ["42"]),
            "210000": ("岐阜県", ["48"]),
            "220000": ("静岡県", ["49"]),
            "230000": ("愛知県", ["50"]),
            "240000": ("三重県", ["51"]),
            "250000": ("滋賀県", ["52"]),
            "260000": ("京都府", ["53"]),
            "270000": ("大阪府", ["54"]),
            "280000": ("兵庫県", ["55"]),
            "290000": ("奈良県", ["56"]),
            "300000": ("和歌山県", ["57"]),
            "310000": ("鳥取県", ["60"]),
            "320000": ("島根県", ["61"]),
            "330000": ("岡山県", ["62"]),
            "340000": ("広島県", ["63"]),
            "350000": ("山口県", ["64"]),
            "360000": ("徳島県", ["65"]),
            "370000": ("香川県", ["66"]),
            "380000": ("愛媛県", ["67"]),
            "390000": ("高知県", ["68"]),
            "400000": ("福岡県", ["71"]),
            "410000": ("佐賀県", ["72"]),
            "420000": ("長崎県", ["73"]),
            "430000": ("熊本県", ["74"]),
            "440000": ("大分県", ["81"]),
            "450000": ("宮崎県", ["82"]),
            "460000": ("鹿児島県", ["83", "84"]),
            "471000": ("沖縄県", ["85", "86", "87", "88", "92", "93"]),
        }
        
        self.station_table = None
        self.cache = {}
        self.cache_duration = 300  # 5 minutes
    
    async def get_latest_time(self) -> Optional[str]:
        """Get the latest observation time"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.latest_time_url, timeout=10) as response:
                    if response.status == 200:
                        time_str = await response.text()
                        return time_str.strip()
                    else:
                        logger.error(f"Failed to get latest time: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Error getting latest time: {e}")
            return None
    
    async def get_station_table(self) -> Dict[str, Any]:
        """Get AMeDAS station information table"""
        if self.station_table:
            return self.station_table
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.table_url, timeout=10) as response:
                    if response.status == 200:
                        self.station_table = await response.json()
                        logger.info(f"Loaded station table with {len(self.station_table)} stations")
                        return self.station_table
                    else:
                        logger.error(f"Failed to get station table: {response.status}")
                        return {}
        except Exception as e:
            logger.error(f"Error getting station table: {e}")
            return {}
    
    async def get_map_data(self, timestamp: str) -> Dict[str, Any]:
        """Get map data for a specific timestamp"""
        # Convert ISO timestamp to the format JMA expects: YYYYMMDDHHMM
        # Example: 2025-11-12T18:20:00+09:00 -> 202511121820
        try:
            from datetime import datetime as dt
            # Parse the ISO timestamp
            if 'T' in timestamp:
                # Remove timezone info and convert
                timestamp_clean = timestamp.split('+')[0].split('Z')[0]
                dt_obj = dt.fromisoformat(timestamp_clean)
                formatted_time = dt_obj.strftime("%Y%m%d%H%M00")
            else:
                formatted_time = timestamp
            
            url = f"{self.map_data_url}/{formatted_time}.json"
            logger.debug(f"Fetching map data from: {url}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.error(f"Failed to get map data: {response.status} from {url}")
                        return {}
        except Exception as e:
            logger.error(f"Error getting map data: {e}")
            return {}
    
    def _convert_wind_direction(self, degrees: Optional[float]) -> Optional[str]:
        """Convert wind direction from degrees to Japanese 16-direction"""
        if degrees is None:
            return None
        
        directions = [
            "北", "北北東", "北東", "東北東",
            "東", "東南東", "南東", "南南東",
            "南", "南南西", "南西", "西南西",
            "西", "西北西", "北西", "北北西"
        ]
        
        index = round(degrees / 22.5) % 16
        return directions[index]
    
    def _get_value(self, data: Any, default: str = "---") -> str:
        """Extract value from data array or return default"""
        if data is None:
            return default
        if isinstance(data, list) and len(data) > 0:
            value = data[0]
            if value is None:
                return default
            return str(value)
        return default
    
    async def get_all_regions_data(self) -> List[AMeDASRegionData]:
        """Get AMeDAS data for all regions"""
        latest_time = await self.get_latest_time()
        if not latest_time:
            logger.error("Could not get latest observation time")
            return []
        
        station_table = await self.get_station_table()
        if not station_table:
            logger.error("Could not get station table")
            return []
        
        map_data = await self.get_map_data(latest_time)
        if not map_data:
            logger.error("Could not get map data")
            return []
        
        # Group stations by region
        region_observations = {}
        
        for station_id, observation_data in map_data.items():
            if station_id not in station_table:
                continue
            
            station_info = station_table[station_id]
            location_name = station_info.get("kjName", station_id)
            
            # Determine region based on station ID prefix (first 2 digits)
            region_code = station_id[:2]
            region_name = self.region_codes.get(region_code, f"不明({region_code})")
            
            # Extract observation data
            temp = observation_data.get("temp")
            precipitation = observation_data.get("precipitation1h")
            wind = observation_data.get("wind")
            sun = observation_data.get("sun1h")
            snow = observation_data.get("snow")
            humidity = observation_data.get("humidity")
            pressure = observation_data.get("pressure")
            normalPressure = observation_data.get("normalPressure")
            
            # Parse wind data
            wind_speed = None
            wind_direction = None
            if wind:
                # Wind data can be either a dict or a list
                if isinstance(wind, dict):
                    wind_speed_val = wind.get("windSpeed")
                    wind_speed = self._get_value(wind_speed_val)
                    
                    wind_dir_deg = wind.get("windDirection")
                    if wind_dir_deg and isinstance(wind_dir_deg, list) and wind_dir_deg[0] is not None:
                        wind_direction = self._convert_wind_direction(wind_dir_deg[0])
                elif isinstance(wind, list) and len(wind) >= 2:
                    # If wind is a list, format is [speed, direction]
                    if wind[0] is not None:
                        wind_speed = str(wind[0])
                    if wind[1] is not None:
                        wind_direction = self._convert_wind_direction(wind[1])
            
            observation = AMeDASObservation(
                location_name=location_name,
                location_id=station_id,
                temperature=self._get_value(temp),
                precipitation_1h=self._get_value(precipitation),
                wind_direction=wind_direction or "---",
                wind_speed=wind_speed,
                sunshine_duration_1h=self._get_value(sun),
                snow_depth=self._get_value(snow),
                humidity=self._get_value(humidity),
                local_pressure=self._get_value(pressure),
                sea_level_pressure=self._get_value(normalPressure),
                observation_time=latest_time,
                region_name=region_name
            )
            
            if region_code not in region_observations:
                region_observations[region_code] = []
            region_observations[region_code].append(observation)
        
        # Create region data objects and sort them
        result = []
        for region_code in sorted(region_observations.keys()):
            observations = region_observations[region_code]
            # Sort observations by location_id for consistency
            observations.sort(key=lambda x: x.location_id)
            
            region_data = AMeDASRegionData(
                region_name=self.region_codes.get(region_code, "不明"),
                region_code=region_code,
                observation_time=latest_time,
                observations=observations
            )
            result.append(region_data)
        
        logger.info(f"Retrieved data for {len(result)} regions with {sum(len(r.observations) for r in result)} total observations")
        return result
    
    async def get_region_data(self, region_code: str) -> Optional[AMeDASRegionData]:
        """Get AMeDAS data for a specific region"""
        all_data = await self.get_all_regions_data()
        
        for region in all_data:
            if region.region_code == region_code:
                return region
        
        return None
    
    async def get_prefecture_data(self, prefecture_code: str) -> Optional[AMeDASRegionData]:
        """
        Get AMeDAS data for a prefecture (e.g., "010000" for Hokkaido)
        Groups all sub-regions within the prefecture
        """
        if prefecture_code not in self.prefecture_codes:
            logger.error(f"Unknown prefecture code: {prefecture_code}")
            return None
        
        all_data = await self.get_all_regions_data()
        
        pref_name, region_prefixes = self.prefecture_codes[prefecture_code]
        
        # Collect all observations for this prefecture
        prefecture_observations = []
        for region in all_data:
            if region.region_code in region_prefixes:
                prefecture_observations.extend(region.observations)
        
        if not prefecture_observations:
            return None
        
        # Sort observations by location_id for consistency
        prefecture_observations.sort(key=lambda x: x.location_id)
        
        # Get latest observation time
        latest_time = prefecture_observations[0].observation_time if prefecture_observations else None
        
        return AMeDASRegionData(
            region_name=pref_name,
            region_code=prefecture_code,
            observation_time=latest_time,
            observations=prefecture_observations
        )
    
    async def get_hokkaido_data(self) -> Optional[AMeDASRegionData]:
        """Get AMeDAS data for Hokkaido (010000)"""
        return await self.get_prefecture_data("010000")


class JMAAMeDASService:
    """Service for managing JMA AMeDAS data"""
    
    def __init__(self):
        self.api = JMAAMeDASAPI()
        self.cache = {}
        self.cache_time = None
        self.cache_duration = 300  # 5 minutes
    
    async def get_all_data(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Get all AMeDAS data"""
        # Check cache
        if not force_refresh and self.cache and self.cache_time:
            age = (datetime.now() - self.cache_time).total_seconds()
            if age < self.cache_duration:
                logger.info(f"Returning cached data (age: {age:.1f}s)")
                return self.cache.get('data', [])
        
        # Fetch fresh data
        regions_data = await self.api.get_all_regions_data()
        
        # Convert to dict format
        result = []
        for region in regions_data:
            region_dict = {
                "region_name": region.region_name,
                "region_code": region.region_code,
                "observation_time": region.observation_time,
                "observations": [asdict(obs) for obs in region.observations]
            }
            result.append(region_dict)
        
        # Update cache
        self.cache = {'data': result}
        self.cache_time = datetime.now()
        
        return result
    
    async def get_region_data(self, region_code: str) -> Optional[Dict[str, Any]]:
        """Get data for a specific region"""
        all_data = await self.get_all_data()
        
        for region in all_data:
            if region['region_code'] == region_code:
                return region
        
        return None
    
    async def get_prefecture_data(self, prefecture_code: str) -> Optional[Dict[str, Any]]:
        """Get data for a prefecture (e.g., '010000' for Hokkaido)"""
        prefecture_data = await self.api.get_prefecture_data(prefecture_code)
        
        if not prefecture_data:
            return None
        
        return {
            "region_name": prefecture_data.region_name,
            "region_code": prefecture_data.region_code,
            "observation_time": prefecture_data.observation_time,
            "observations": [asdict(obs) for obs in prefecture_data.observations]
        }
    
    async def export_to_json(self, filename: str = "amedas_data.json", sort_keys: bool = False):
        """
        Export all AMeDAS data to JSON file
        
        Args:
            filename: Output filename
            sort_keys: If True, sort dictionary keys in output (default: False to maintain insertion order)
        """
        data = await self.get_all_data(force_refresh=True)
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=sort_keys)
        
        total_observations = sum(len(region['observations']) for region in data)
        logger.info(f"Exported {len(data)} regions with {total_observations} observations to {filename}")
        return filename
    
    async def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics of AMeDAS data"""
        all_data = await self.get_all_data()
        
        total_regions = len(all_data)
        total_observations = sum(len(region['observations']) for region in all_data)
        
        # Find extremes
        all_temps = []
        all_winds = []
        all_precip = []
        
        for region in all_data:
            for obs in region['observations']:
                try:
                    if obs['temperature'] and obs['temperature'] != '---':
                        all_temps.append((float(obs['temperature']), obs['location_name'], region['region_name']))
                except:
                    pass
                
                try:
                    if obs['wind_speed'] and obs['wind_speed'] != '---':
                        all_winds.append((float(obs['wind_speed']), obs['location_name'], region['region_name']))
                except:
                    pass
                
                try:
                    if obs['precipitation_1h'] and obs['precipitation_1h'] != '---':
                        all_precip.append((float(obs['precipitation_1h']), obs['location_name'], region['region_name']))
                except:
                    pass
        
        summary = {
            "total_regions": total_regions,
            "total_observations": total_observations,
            "observation_time": all_data[0]['observation_time'] if all_data else None,
        }
        
        if all_temps:
            all_temps.sort()
            summary["temperature"] = {
                "min": {"value": all_temps[0][0], "location": all_temps[0][1], "region": all_temps[0][2]},
                "max": {"value": all_temps[-1][0], "location": all_temps[-1][1], "region": all_temps[-1][2]},
                "avg": sum(t[0] for t in all_temps) / len(all_temps)
            }
        
        if all_winds:
            all_winds.sort(reverse=True)
            summary["wind_speed"] = {
                "max": {"value": all_winds[0][0], "location": all_winds[0][1], "region": all_winds[0][2]},
                "top_10": [{"value": w[0], "location": w[1], "region": w[2]} for w in all_winds[:10]]
            }
        
        if all_precip:
            all_precip.sort(reverse=True)
            summary["precipitation"] = {
                "max": {"value": all_precip[0][0], "location": all_precip[0][1], "region": all_precip[0][2]},
                "top_10": [{"value": p[0], "location": p[1], "region": p[2]} for p in all_precip[:10]]
            }
        
        return summary


# Global service instance
_service = None

def get_amedas_service() -> JMAAMeDASService:
    """Get or create the AMeDAS service singleton"""
    global _service
    if _service is None:
        _service = JMAAMeDASService()
    return _service


# CLI and testing functions
async def main():
    """Main function for testing (uses JSON API)"""
    service = get_amedas_service()
    
    print("=" * 80)
    print("JMA AMeDAS Data Scraper (JSON API)")
    print("=" * 80)
    
    # Get summary
    print("\nFetching data summary...")
    summary = await service.get_summary()
    print(f"\nTotal Regions: {summary['total_regions']}")
    print(f"Total Observations: {summary['total_observations']}")
    print(f"Observation Time: {summary['observation_time']}")
    
    if 'temperature' in summary:
        temp = summary['temperature']
        print(f"\nTemperature:")
        print(f"  Min: {temp['min']['value']}°C at {temp['min']['location']} ({temp['min']['region']})")
        print(f"  Max: {temp['max']['value']}°C at {temp['max']['location']} ({temp['max']['region']})")
        print(f"  Avg: {temp['avg']:.1f}°C")
    
    if 'wind_speed' in summary:
        wind = summary['wind_speed']
        print(f"\nWind Speed:")
        print(f"  Max: {wind['max']['value']}m/s at {wind['max']['location']} ({wind['max']['region']})")
        print(f"  Top 10 Windiest:")
        for i, w in enumerate(wind['top_10'][:5], 1):
            print(f"    {i}. {w['location']} ({w['region']}): {w['value']}m/s")
    
    if 'precipitation' in summary:
        precip = summary['precipitation']
        print(f"\nPrecipitation (1h):")
        print(f"  Max: {precip['max']['value']}mm at {precip['max']['location']} ({precip['max']['region']})")
    
    # Get Hokkaido data (prefecture code: 010000)
    print("\n" + "=" * 80)
    print("Hokkaido Prefecture Data Sample")
    print("=" * 80)
    hokkaido_data = await service.get_prefecture_data("010000")
    
    if hokkaido_data:
        print(f"\nPrefecture: {hokkaido_data['region_name']}")
        print(f"Observation Time: {hokkaido_data['observation_time']}")
        print(f"Total Observations: {len(hokkaido_data['observations'])}")
        print("\nFirst 10 observations (sorted by station ID):")
        print(f"{'Station ID':<12} {'Location':<20} {'Temp':<8} {'Precip':<8} {'Wind Dir':<8} {'Wind Spd':<10}")
        print("-" * 85)
        
        for obs in hokkaido_data['observations'][:10]:
            print(f"{obs['location_id']:<12} {obs['location_name']:<20} {obs['temperature']:<8} {obs['precipitation_1h']:<8} "
                  f"{obs['wind_direction']:<8} {obs['wind_speed']:<10}")
    
    # Export to JSON
    print("\n" + "=" * 80)
    print("Exporting data to JSON...")
    filename = await service.export_to_json()
    print(f"Data exported to: {filename}")
    print("=" * 80)


def test_selenium_scraper():
    """Test function for Selenium scraper"""
    print("=" * 80)
    print("JMA AMeDAS Selenium Scraper Test")
    print("=" * 80)
    
    scraper = JMAAMeDASSeleniumScraper(headless=True)
    
    # Test scraping Hokkaido (010000)
    print("\nScraping Hokkaido (北海道) data...")
    print("-" * 80)
    
    hokkaido_data = scraper.scrape_prefecture("010000")
    
    if hokkaido_data:
        print(f"\n✓ Successfully scraped {len(hokkaido_data)} regions")
        
        total_observations = sum(len(region['observations']) for region in hokkaido_data)
        print(f"✓ Total observations: {total_observations}")
        
        # Display data for first region
        if hokkaido_data[0]['observations']:
            first_region = hokkaido_data[0]
            print(f"\n{'='*80}")
            print(f"Region: {first_region['region_name']}")
            print(f"Observation Time: {first_region['observation_time']}")
            print(f"Total Stations: {len(first_region['observations'])}")
            print(f"{'='*80}\n")
            
            print(f"{'Station ID':<12} {'Location':<20} {'Temp(°C)':<10} {'Precip(mm)':<12} {'Wind':<10} {'Speed(m/s)':<12}")
            print("-" * 95)
            
            for obs in first_region['observations'][:15]:  # Show first 15 observations
                print(f"{obs['location_id']:<12} {obs['location_name']:<20} "
                      f"{obs['temperature']:<10} {obs['precipitation_1h']:<12} "
                      f"{obs['wind_direction']:<10} {obs['wind_speed']:<12}")
        
        # Export to JSON
        print(f"\n{'='*80}")
        print("Exporting to JSON...")
        output_file = "amedas_selenium_test.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(hokkaido_data, f, ensure_ascii=False, indent=2)
        print(f"✓ Data exported to: {output_file}")
        print(f"{'='*80}")
        
    else:
        print("✗ Failed to scrape data")
    
    print("\nTest completed!")


async def main_selenium():
    """Main function for Selenium scraper that exports data"""
    print("=" * 80)
    print("JMA AMeDAS Data Scraper (Selenium)")
    print("=" * 80)
    
    scraper = JMAAMeDASSeleniumScraper(headless=True)
    
    # Scrape all prefectures
    print("\nScraping all prefectures...")
    all_data = scraper.scrape_all_prefectures()
    
    if all_data:
        total_observations = sum(len(region['observations']) for region in all_data)
        print(f"\n✓ Successfully scraped {len(all_data)} regions")
        print(f"✓ Total observations: {total_observations}")
        
        # Show sample from first region
        if all_data and all_data[0]['observations']:
            first_region = all_data[0]
            print(f"\n{'='*80}")
            print(f"Sample Region: {first_region['region_name']}")
            print(f"Observation Time: {first_region['observation_time']}")
            print(f"Prefecture: {first_region.get('prefecture_name', 'N/A')}")
            print(f"{'='*80}\n")
            
            print(f"{'Location':<20} {'Temp(°C)':<10} {'Precip(mm)':<12} {'Wind Dir':<12} {'Wind Speed(m/s)':<15}")
            print("-" * 85)
            
            for obs in first_region['observations'][:10]:
                print(f"{obs['location_name']:<20} "
                      f"{obs['temperature']:<10} {obs['precipitation_1h']:<12} "
                      f"{obs['wind_direction']:<12} {obs['wind_speed']:<15}")
        
        # Export to JSON
        print(f"\n{'='*80}")
        print("Exporting data to JSON...")
        output_file = "amedas_data.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
        print(f"✓ Data exported to: {output_file}")
        print(f"✓ Total regions: {len(all_data)}")
        print(f"✓ Total observations: {total_observations}")
        print(f"{'='*80}")
    else:
        print("✗ Failed to scrape data")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--api':
        # Run JSON API scraper
        asyncio.run(main())
    elif len(sys.argv) > 1 and sys.argv[1] == '--test-selenium':
        # Run Selenium scraper test (single prefecture)
        test_selenium_scraper()
    else:
        # Run Selenium scraper for all prefectures (default)
        asyncio.run(main_selenium())

