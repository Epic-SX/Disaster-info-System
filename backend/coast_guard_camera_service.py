import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from bs4 import BeautifulSoup


class CoastGuardCameraService:
    """Scrapes Japan Coast Guard camstream site and builds stream metadata."""

    BASE_URL = "https://camera.mics.kaiho.mlit.go.jp"
    LIST_ENDPOINT = "/camstream/"
    CACHE_TTL_SECONDS = 300

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        self._cache: List[Dict[str, Any]] = []
        self._cache_expiry: datetime = datetime.min
        self._location_index = self._load_location_metadata()

    def _load_location_metadata(self) -> Dict[str, Dict[str, Any]]:
        """Load static latitude/longitude metadata for each camera."""
        try:
            data_path = Path(__file__).parent / "data" / "coast_guard_camera_locations.json"
            with data_path.open("r", encoding="utf-8") as fp:
                data: List[Dict[str, Any]] = json.load(fp)
            return {item["slug"]: item for item in data}
        except FileNotFoundError:
            self.logger.warning("Camera location metadata not found, map labels will be limited")
            return {}
        except Exception as exc:
            self.logger.error(f"Failed to load camera location metadata: {exc}")
            return {}

    async def get_camera_feeds(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Return cached camera feeds or scrape the upstream site."""
        if (
            not force_refresh
            and self._cache
            and datetime.utcnow() < self._cache_expiry
        ):
            return self._cache

        feeds = await self._scrape_camera_list()
        self._cache = feeds
        self._cache_expiry = datetime.utcnow() + timedelta(seconds=self.CACHE_TTL_SECONDS)
        return feeds

    async def warm_cache(self) -> None:
        """Populate cache during application startup."""
        try:
            await self.get_camera_feeds(force_refresh=True)
        except Exception as exc:
            self.logger.warning(f"Unable to warm camera feed cache: {exc}")

    async def _scrape_camera_list(self) -> List[Dict[str, Any]]:
        """Scrape the list of camstream endpoints and build feed metadata."""
        self.logger.info("Fetching Japan Coast Guard camera list")
        headers = {"User-Agent": "disaster-info-system/1.0"}
        feeds: List[Dict[str, Any]] = []
        now = datetime.utcnow()

        async with httpx.AsyncClient(headers=headers, timeout=20.0) as client:
            response = await client.get(f"{self.BASE_URL}{self.LIST_ENDPOINT}")
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            for anchor in soup.select("ol li a"):
                name = anchor.get_text(strip=True)
                href = anchor.get("href")
                if not href:
                    continue

                slug = href.strip("/").split("/")[-1]
                location_meta = self._location_index.get(slug, {})
                lat = location_meta.get("latitude")
                lng = location_meta.get("longitude")
                location_label = location_meta.get("location") or name

                feed = {
                    "id": slug,
                    "name": name,
                    "status": "online",
                    "location": location_label,
                    # Use proxy URL to bypass CORS restrictions
                    "stream_url": f"/api/camera-proxy/realmovie/{slug}-live.m3u8",
                    "thumbnail_url": f"{self.BASE_URL}/thumbnail/{slug}.jpg",
                    "last_updated": now,
                    "coordinates": (
                        {"lat": lat, "lng": lng} if lat is not None and lng is not None else None
                    ),
                }
                feeds.append(feed)

        self.logger.info("Loaded %d coastal camera feeds", len(feeds))
        return feeds

