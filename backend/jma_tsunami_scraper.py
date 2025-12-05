#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JMA Tsunami Information Scraper
Scrapes tsunami warning/advisory information from JMA website using Selenium
https://www.jma.go.jp/bosai/map.html#5/37.979/135/&elem=warn&contents=tsunami
"""

import logging
import time
import re
import os
from datetime import datetime
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass, asdict
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class TsunamiStatus:
    """Tsunami status information"""
    message: str
    has_warning: bool
    warning_type: Optional[str] = None  # "大津波警報", "津波警報", "津波注意報", "津波予報", or None
    affected_areas: List[str] = None
    timestamp: datetime = None
    source: str = "JMA"


class JMATsunamiScraper:
    """Selenium-based scraper for JMA tsunami information"""
    
    def __init__(self, headless: bool = True):
        """
        Initialize the Selenium scraper
        
        Args:
            headless: Run browser in headless mode (default: True)
        """
        self.base_url = "https://www.jma.go.jp/bosai/map.html#5/37.979/135/&elem=warn&contents=tsunami"
        self.headless = headless
        self.driver = None
        
    def _setup_driver(self):
        """Setup Chrome driver with appropriate options"""
        try:
            chrome_options = Options()
            
            # Essential flags for server/Docker environments
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-software-rasterizer')
            chrome_options.add_argument('--disable-extensions')
            
            # Headless mode configuration
            if self.headless:
                chrome_options.add_argument('--headless=new')
                # Try with remote debugging port (fixes DevToolsActivePort issue)
                import random
                debug_port = random.randint(9223, 9322)
                try:
                    chrome_options.add_argument(f'--remote-debugging-port={debug_port}')
                    logger.info(f"Using remote debugging port: {debug_port}")
                except:
                    # If port is already in use, try without it
                    logger.warning("Could not set remote debugging port, continuing without it")
            
            # Additional stability flags
            chrome_options.add_argument('--disable-background-timer-throttling')
            chrome_options.add_argument('--disable-backgrounding-occluded-windows')
            chrome_options.add_argument('--disable-renderer-backgrounding')
            chrome_options.add_argument('--disable-features=TranslateUI')
            chrome_options.add_argument('--disable-ipc-flooding-protection')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            
            # User agent
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            # Experimental options
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            prefs = {
                "profile.default_content_setting_values.notifications": 2,
                "profile.default_content_settings.popups": 0
            }
            chrome_options.add_experimental_option("prefs", prefs)
            
            logger.info("Installing/Checking ChromeDriver...")
            
            # Try to find Chrome/Chromium binary
            chrome_binary = None
            possible_paths = [
                '/usr/bin/google-chrome',
                '/usr/bin/chromium-browser',
                '/usr/bin/chromium',
                '/snap/bin/chromium'
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    chrome_binary = path
                    logger.info(f"Found Chrome/Chromium at: {chrome_binary}")
                    break
            
            if chrome_binary:
                chrome_options.binary_location = chrome_binary
                logger.info(f"Using Chrome binary: {chrome_binary}")
            else:
                logger.warning("Chrome/Chromium binary not found in standard locations, using system default")
            
            # Get Chrome version and install matching ChromeDriver
            try:
                import subprocess
                # Try to get Chrome version
                chrome_version = None
                if chrome_binary:
                    try:
                        result = subprocess.run(
                            [chrome_binary, '--version'],
                            capture_output=True,
                            text=True,
                            timeout=5
                        )
                        if result.returncode == 0:
                            # Extract version number (e.g., "Chromium 142.0.7444.175" -> "142.0.7444.175")
                            version_match = re.search(r'(\d+)\.(\d+)\.(\d+)\.(\d+)', result.stdout)
                            if version_match:
                                chrome_version = version_match.group(0)
                                logger.info(f"Detected Chrome version: {chrome_version}")
                    except Exception as e:
                        logger.warning(f"Could not detect Chrome version: {e}")
                
                # Install ChromeDriver - For Chrome 115+, use ChromeType.CHROMIUM
                # ChromeDriverManager needs proper Chrome type detection for Chromium
                try:
                    if chrome_version:
                        logger.info(f"Installing ChromeDriver for Chrome version: {chrome_version}")
                    
                    # Use ChromeType.CHROMIUM since we're using chromium-browser
                    # This helps webdriver-manager detect the version correctly
                    try:
                        driver_path = ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()
                        logger.info(f"ChromeDriver installed (Chromium type) at: {driver_path}")
                    except Exception as e1:
                        logger.warning(f"Failed with ChromeType.CHROMIUM: {e1}, trying default")
                        # Fall back to default (should auto-detect)
                        driver_path = ChromeDriverManager().install()
                        logger.info(f"ChromeDriver installed (default) at: {driver_path}")
                except Exception as e:
                    logger.error(f"ChromeDriverManager failed: {e}", exc_info=True)
                    raise
                
                service = Service(driver_path)
            except Exception as e:
                logger.error(f"Failed to install ChromeDriver: {e}", exc_info=True)
                raise
            
            # Create driver with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    self.driver = webdriver.Chrome(service=service, options=chrome_options)
                    break
                except Exception as e:
                    if attempt < max_retries - 1:
                        logger.warning(f"Attempt {attempt + 1} failed, retrying... Error: {e}")
                        time.sleep(2)
                    else:
                        raise
            
            # Set longer timeouts
            self.driver.set_page_load_timeout(60)
            self.driver.implicitly_wait(10)
            
            logger.info("Chrome driver initialized successfully")
            
        except Exception as e:
            logger.error(f"Error setting up Chrome driver: {e}", exc_info=True)
            raise
    
    def _close_driver(self):
        """Close the Chrome driver"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Chrome driver closed")
            except Exception as e:
                logger.error(f"Error closing driver: {e}")
    
    def scrape_tsunami_status(self) -> Optional[TsunamiStatus]:
        """
        Scrape tsunami status from JMA website
        
        Returns:
            TsunamiStatus object with current tsunami information, or None if scraping fails
        """
        if not self.driver:
            try:
                self._setup_driver()
            except Exception as e:
                logger.error(f"Failed to setup Chrome driver: {e}")
                return None
        
        try:
            logger.info(f"Navigating to JMA tsunami page: {self.base_url}")
            self.driver.get(self.base_url)
            
            # Wait for the page to load and JavaScript to render
            # The element we're looking for is #unitmap-centertext
            wait = WebDriverWait(self.driver, 45)  # Increased timeout
            
            # Wait for the center text element to appear
            logger.info("Waiting for tsunami status element to load...")
            try:
                center_text_element = wait.until(
                    EC.presence_of_element_located((By.ID, "unitmap-centertext"))
                )
            except TimeoutException:
                logger.warning("Timeout waiting for #unitmap-centertext, trying alternative selectors...")
                # Try alternative: wait for any element with class containing "centertext"
                try:
                    center_text_element = wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "[id*='centertext'], [class*='centertext']"))
                    )
                    logger.info("Found element using alternative selector")
                except TimeoutException:
                    logger.error("Could not find tsunami status element with any selector")
                    # Take a screenshot for debugging
                    try:
                        self.driver.save_screenshot('/tmp/jma_tsunami_debug.png')
                        logger.info("Saved debug screenshot to /tmp/jma_tsunami_debug.png")
                    except:
                        pass
                    return None
            
            # Additional wait to ensure content is fully rendered
            time.sleep(5)  # Increased wait time
            
            # Try to get text from inner div first, then fall back to the element itself
            message = ""
            try:
                # Look for inner div with the actual message
                inner_div = center_text_element.find_element(By.TAG_NAME, "div")
                message = inner_div.text.strip()
                logger.info(f"Found message in inner div: {message[:50]}...")
            except NoSuchElementException:
                # Fall back to the element's own text
                message = center_text_element.text.strip()
                logger.info(f"Using element text directly: {message[:50]}...")
            
            if not message:
                # If still no message, try getting all text from the element
                message = center_text_element.get_attribute("textContent") or center_text_element.get_attribute("innerText") or ""
                message = message.strip()
                logger.info(f"Using textContent/innerText: {message[:50]}...")
            
            if not message or len(message) < 5:
                logger.warning(f"Message is too short or empty: '{message}'")
                # Try waiting a bit more and retry
                time.sleep(3)
                message = center_text_element.text.strip()
                if not message:
                    message = center_text_element.get_attribute("textContent") or ""
                    message = message.strip()
            
            if not message or len(message) < 5:
                logger.error("Could not extract valid message from element")
                return None
            
            logger.info(f"Scraped tsunami status message: {message[:100]}...")
            
            # Parse the message to determine warning status
            has_warning, warning_type, affected_areas = self._parse_tsunami_message(message)
            
            status = TsunamiStatus(
                message=message,
                has_warning=has_warning,
                warning_type=warning_type,
                affected_areas=affected_areas or [],
                timestamp=datetime.now(),
                source="JMA"
            )
            
            return status
            
        except TimeoutException as e:
            logger.error(f"Timeout waiting for tsunami status element: {e}")
            return None
        except NoSuchElementException as e:
            logger.error(f"Element not found: {e}")
            return None
        except Exception as e:
            logger.error(f"Error scraping tsunami status: {e}", exc_info=True)
            return None
    
    def _parse_tsunami_message(self, message: str) -> Tuple[bool, Optional[str], List[str]]:
        """
        Parse the tsunami status message to extract warning information
        
        Args:
            message: The scraped message text
            
        Returns:
            Tuple of (has_warning, warning_type, affected_areas)
        """
        # Check if message indicates no warnings
        no_warning_patterns = [
            r"発表していません",
            r"発表されていません",
            r"現在.*ありません"
        ]
        
        for pattern in no_warning_patterns:
            if re.search(pattern, message):
                return (False, None, [])
        
        # Check for different warning types
        warning_types = {
            "大津波警報": r"大津波警報",
            "津波警報": r"津波警報",
            "津波注意報": r"津波注意報",
            "津波予報": r"津波予報"
        }
        
        detected_type = None
        for warning_name, pattern in warning_types.items():
            if re.search(pattern, message):
                detected_type = warning_name
                break
        
        # Extract affected areas (prefecture names)
        # Japanese prefecture pattern
        prefecture_pattern = r"([都道府県]+)"
        affected_areas = re.findall(prefecture_pattern, message)
        
        # If we found a warning type, we have a warning
        has_warning = detected_type is not None
        
        return (has_warning, detected_type, affected_areas)
    
    def get_tsunami_status(self) -> Optional[TsunamiStatus]:
        """
        Public method to get tsunami status (handles driver lifecycle)
        
        Returns:
            TsunamiStatus object or None
        """
        try:
            return self.scrape_tsunami_status()
        finally:
            self._close_driver()


# Async wrapper for use in async contexts
async def get_jma_tsunami_status(headless: bool = True) -> Optional[TsunamiStatus]:
    """
    Async wrapper to get JMA tsunami status
    
    Args:
        headless: Run browser in headless mode
        
    Returns:
        TsunamiStatus object or None
    """
    import asyncio
    
    def _scrape():
        scraper = JMATsunamiScraper(headless=headless)
        return scraper.get_tsunami_status()
    
    # Run in thread pool to avoid blocking
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _scrape)


if __name__ == "__main__":
    # Test the scraper
    scraper = JMATsunamiScraper(headless=True)
    status = scraper.get_tsunami_status()
    
    if status:
        print(f"Message: {status.message}")
        print(f"Has Warning: {status.has_warning}")
        print(f"Warning Type: {status.warning_type}")
        print(f"Affected Areas: {status.affected_areas}")
        print(f"Timestamp: {status.timestamp}")
    else:
        print("Failed to scrape tsunami status")

