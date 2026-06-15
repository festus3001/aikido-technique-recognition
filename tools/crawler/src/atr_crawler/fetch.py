"""Polite cached fetching: robots.txt, rate limit, on-disk cache.

A crawl is re-run on a schedule, so fetches are cached to disk by URL and reused
unless explicitly refreshed. robots.txt is honored per host, and requests to a
host are spaced by a minimum delay. `requests` is imported lazily so the rest of
the package (models, store, co-presence) works without it installed.

If a source's terms forbid reproduction, the caller records only the citation,
not the cached content -- the cache is a fetch optimization, not a data store
that ships.
"""

from __future__ import annotations

import hashlib
import time
import urllib.robotparser
from pathlib import Path
from urllib.parse import urlparse

DEFAULT_UA = "ATR-datamap-crawler/0.1 (+https://github.com/; aikido lineage map; contact project owner)"


class Fetcher:
    def __init__(
        self,
        cache_dir: str | Path,
        user_agent: str = DEFAULT_UA,
        min_delay: float = 2.0,
        timeout: float = 30.0,
        respect_robots: bool = True,
    ):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.user_agent = user_agent
        self.min_delay = min_delay
        self.timeout = timeout
        self.respect_robots = respect_robots
        self._last_hit: dict[str, float] = {}
        self._robots: dict[str, urllib.robotparser.RobotFileParser] = {}

    def _cache_path(self, url: str) -> Path:
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
        return self.cache_dir / f"{digest}.html"

    def _allowed(self, url: str) -> bool:
        if not self.respect_robots:
            return True
        parsed = urlparse(url)
        host = f"{parsed.scheme}://{parsed.netloc}"
        if host not in self._robots:
            self._robots[host] = self._load_robots(host)
        rp = self._robots[host]
        return True if rp is None else rp.can_fetch(self.user_agent, url)

    def _load_robots(self, host: str):
        """Fetch robots.txt with our own UA (urllib's default UA is blocked by
        some hosts, which then read as 403 -> disallow-all). Return a parser, or
        None to allow when robots.txt is missing or unreadable."""
        try:
            import requests
            resp = requests.get(f"{host}/robots.txt",
                                 headers={"User-Agent": self.user_agent}, timeout=self.timeout)
        except Exception:
            return None
        if resp.status_code != 200 or not resp.text.strip():
            return None
        rp = urllib.robotparser.RobotFileParser()
        rp.parse(resp.text.splitlines())
        return rp

    def _throttle(self, url: str) -> None:
        host = urlparse(url).netloc
        last = self._last_hit.get(host)
        if last is not None:
            wait = self.min_delay - (time.monotonic() - last)
            if wait > 0:
                time.sleep(wait)
        self._last_hit[host] = time.monotonic()

    def get(self, url: str, refresh: bool = False) -> str | None:
        """Return page text from cache or network. None if disallowed/failed."""
        cache_path = self._cache_path(url)
        if cache_path.exists() and not refresh:
            return cache_path.read_text(encoding="utf-8", errors="replace")

        if not self._allowed(url):
            print(f"SKIP (robots.txt disallows): {url}")
            return None

        try:
            import requests
        except ImportError as exc:
            raise RuntimeError("network fetch requires `requests` (pip install requests)") from exc

        self._throttle(url)
        try:
            resp = requests.get(url, headers={"User-Agent": self.user_agent}, timeout=self.timeout)
            resp.raise_for_status()
        except Exception as exc:  # noqa: BLE001 -- log and continue the crawl
            print(f"FETCH FAILED {url}: {exc}")
            return None

        cache_path.write_text(resp.text, encoding="utf-8")
        return resp.text
