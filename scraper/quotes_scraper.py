from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from scraper.interfaces import Scraper

BASE_URL = "https://quotes.toscrape.com"


class QuotesToScrapeScraper(Scraper):
    def __init__(self, base_url: str = BASE_URL, session: requests.Session | None = None):
        self._base_url = base_url
        self._session = session or requests.Session()

    def scrape(self) -> list[dict]:
        records = []
        url = self._base_url
        while url:
            response = self._session.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            records.extend(self._parse_page(soup))
            url = self._next_page_url(soup, current_url=url)
        return records

    def _parse_page(self, soup: BeautifulSoup) -> list[dict]:
        page_records = []
        for quote_div in soup.select(".quote"):
            text = quote_div.select_one(".text").get_text(strip=True)
            author = quote_div.select_one(".author").get_text(strip=True)
            tags = [tag.get_text(strip=True) for tag in quote_div.select(".tags .tag")]
            page_records.append({"text": text, "author": author, "tags": tags})
        return page_records

    def _next_page_url(self, soup: BeautifulSoup, current_url: str) -> str | None:
        next_link = soup.select_one("li.next a")
        if not next_link:
            return None
        return urljoin(current_url, next_link["href"])
