import logging
import hashlib
import traceback
from tempfile import NamedTemporaryFile
from typing import Optional, List
from urllib.parse import urljoin, urlparse, urlunparse

import requests
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import models
from slugify import slugify
from django.utils import timezone

from apps.scraper.services.llm import LLMService

from playwright.sync_api import sync_playwright

logger = logging.getLogger("scraper")


class TaskStatus(models.TextChoices):
    NOT_STARTED = "Not Started", "Not Started"
    IN_PROGRESS = "In Progress", "In Progress"
    SUCCESS = "Success", "Success"
    FAILED = "Failed", "Failed"


class SiteMapping(models.TextChoices):
    GOVEXEC = "govexec.news", "GovExec"
    DEFENSE_ONE = "defenseone.news", "Defense One"
    GLOBALTIMES = "globaltimes.news", "Global Times"
    KOREA_HERALD = "koreaherald.news", "Korea Herald"
    KYIV_INDEPENDENT = "kyivindependent.news", "Kyiv Independent"


class Scraper(models.Model):
    """Model to store the scrapers we want"""

    site = models.CharField(max_length=240, choices=SiteMapping.choices)
    active = models.BooleanField(default=True)

    name = models.CharField(max_length=240, unique=True)
    base_url = models.CharField(max_length=1000, verbose_name="Starting url")
    category = models.CharField(max_length=240, verbose_name="Category")

    # Kept for finding article links on the section page - LLM cant browse pages
    section_container = models.CharField(
        max_length=240, verbose_name="Section Container", null=True, blank=True
    )
    article_item = models.CharField(
        max_length=240, verbose_name="Article Selector Path"
    )
    href_selector = models.CharField(max_length=240, verbose_name="Href selector")

    # Scraper health tracking
    last_run = models.DateTimeField(null=True, blank=True)
    last_success = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(null=True, blank=True)
    total_runs = models.IntegerField(default=0)
    successful_runs = models.IntegerField(default=0)
    failed_runs = models.IntegerField(default=0)

    def __str__(self):
        return self.name

    @property
    def chat_model(self):
        return LLMService()

    @property
    def success_rate(self):
        if self.total_runs == 0:
            return 0
        return (self.successful_runs / self.total_runs) * 100

    def deactivate_scraper(self):
        self.active = False
        self.save()

    # -------------------------------------------------------------------------
    # Page fetching
    # -------------------------------------------------------------------------

    def fetch_page(self, url: str, use_playwright: bool = False) -> Optional[str]:
        """Fetch the HTML content of the given URL."""
        if use_playwright:
            return self._fetch_with_playwright(url)

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Cache-Control": "max-age=0",
        }

        try:
            response = requests.get(
                url, headers=headers, timeout=30, allow_redirects=True
            )
            response.raise_for_status()
            return response.text
        except requests.Timeout:
            raise Exception(f"Timeout fetching {url}")
        except requests.ConnectionError:
            raise Exception(f"Connection error fetching {url}")
        except requests.HTTPError as e:
            status_code = getattr(e.response, "status_code", "unknown")
            msg = f"HTTP {status_code} fetching {url}"
            if status_code == 403:
                msg += " (blocked — may need Playwright)"
            raise Exception(msg)
        except requests.RequestException as e:
            raise Exception(f"Error fetching {url}: {e}")

    def _fetch_with_playwright(self, url: str) -> str:
        """Fetch page content using Playwright as a fallback."""
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-gpu",
                    ],
                )
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                page = context.new_page()
                try:
                    page.goto(url, timeout=60000, wait_until="domcontentloaded")
                    return page.content()
                finally:
                    browser.close()
        except ImportError:
            raise Exception("Playwright is not installed. Add 'playwright' to requirements.txt")

    def fetch_page_with_fallback(self, url: str) -> Optional[str]:
        """Try standard fetch first, fall back to Playwright on failure."""
        try:
            return self.fetch_page(url, use_playwright=False)
        except Exception as e:
            logger.info(f"Standard fetch failed for {url}, retrying with Playwright: {e}")
            return self.fetch_page(url, use_playwright=True)

    # -------------------------------------------------------------------------
    # Section scraping — still uses selectors since we just need hrefs
    # -------------------------------------------------------------------------

    def scrape_section(self) -> List[str]:
        """Scrape the section page and return a list of article URLs."""
        from bs4 import BeautifulSoup

        html = self.fetch_page_with_fallback(self.base_url)
        if not html:
            raise Exception("Failed to fetch section page")

        soup = BeautifulSoup(html, "html.parser")

        if self.section_container:
            container = soup.select_one(self.section_container)
            if not container:
                raise Exception(
                    f"Section container '{self.section_container}' not found"
                )
            items = container.select(self.article_item)
        else:
            items = soup.select(self.article_item)

        if not items:
            raise Exception(f"No items found with selector '{self.article_item}'")

        article_urls = []
        for item in items:
            href_elem = item.select_one(self.href_selector)
            if href_elem and href_elem.has_attr("href"):
                full_url = urljoin(self.base_url, href_elem["href"])
                article_urls.append(full_url)

        if not article_urls:
            raise Exception("Found items but could not extract any hrefs")

        return article_urls

    # -------------------------------------------------------------------------
    # Article extraction — single page fetch, single LLM call
    # -------------------------------------------------------------------------

    def extract_article_data(self, url: str) -> dict:
        """
        Fetch an article page and use the LLM to extract all fields in one shot.
        Returns a dict with keys: title, body, image_url, image_credit
        """
        html = self.fetch_page_with_fallback(url)
        if not html:
            raise Exception(f"Failed to fetch article page: {url}")

        prompt = f"""You are an expert at extracting structured content from news article HTML.

Extract the following fields from the HTML below and return ONLY valid JSON, no explanation:
- title: the article headline
- body: the full article body text (clean text only, no HTML tags)
- image_url: the URL of the main article image (absolute URL if possible, otherwise as-is). null if not found.
- image_credit: the image credit or caption text. null if not found.

HTML:
{html[:12000]}

Return format:
{{
  "title": "...",
  "body": "...",
  "image_url": "...",
  "image_credit": "..."
}}"""

        result = self.chat_model.send_prompt_json(prompt)

        if not result:
            raise Exception("LLM returned no data for article extraction")

        if not result.get("title") or not result.get("body"):
            raise Exception(f"LLM extraction missing title or body: {result}")

        # Ensure image_url is absolute
        if result.get("image_url"):
            result["image_url"] = urljoin(url, result["image_url"])

        return result

    def rephrase_article(self, title: str, body: str) -> dict:
        """
        Rephrase both title and body in a single LLM call to save on API usage.
        Returns a dict with keys: title, body
        """
        prompt = f"""Rephrase the following news article in two parts.

Writing style: an unbiased journalist with a strong mix of tabloid / viral BuzzFeed style

Rules:
- Title: short, punchy, do not explain, just respond with the rephrased title
- Body: HTML format using only <p> tags, minimum 5 paragraphs, first paragraph must be a huge cliffhanger

Return ONLY valid JSON, no explanation:
{{
  "title": "...",
  "body": "<p>...</p><p>...</p>"
}}

Original title: {title}

Original body: {body}"""

        result = self.chat_model.send_prompt_json(prompt)

        if not result:
            raise Exception("LLM returned no data for rephrasing")

        return result

    # -------------------------------------------------------------------------
    # Main scrape entrypoint
    # -------------------------------------------------------------------------

    def start_scrape(self):
        """Start the scraping process."""
        self.last_run = timezone.now()
        self.total_runs += 1
        scrape_successful = True
        error_message = None

        try:
            article_urls: List[str] = self.scrape_section()

            if not article_urls:
                error_message = "No article URLs found. Check selectors."
                logger.warning(f"Scraper '{self.name}': {error_message}")
                scrape_successful = False
            else:
                logger.info(
                    f"Scraper '{self.name}': Found {len(article_urls)} articles"
                )

            for article_url in article_urls:
                # Normalise URL — strip query params for dedup
                parsed = urlparse(article_url)
                clean_url = urlunparse(
                    (parsed.scheme, parsed.netloc, parsed.path, "", "", "")
                )
                query_params = parsed.query or None

                if ScrapedArticle.objects.filter(url=clean_url).exists():
                    continue

                scraped_article = ScrapedArticle(
                    status=TaskStatus.IN_PROGRESS,
                    url=clean_url,
                    query_params=query_params,
                    category=self.category,
                    scraper=self,
                )

                try:
                    self.process_article(article_url, scraped_article)
                    scraped_article.status = TaskStatus.SUCCESS
                    scraped_article.save()

                    logger.info(f"Successfully scraped: {article_url}")

                except Exception as e:
                    error_trace = traceback.format_exc()
                    scraped_article.status = TaskStatus.FAILED
                    scraped_article.message = f"{str(e)}\n\nTraceback:\n{error_trace}"
                    scraped_article.retry_count = 0
                    scraped_article.save()
                    logger.error(
                        f"Error scraping {article_url}: {str(e)}\n{error_trace}"
                    )

            if scrape_successful:
                self.successful_runs += 1
                self.last_success = timezone.now()
                self.last_error = None

        except Exception as e:
            error_trace = traceback.format_exc()
            error_message = f"{str(e)}\n\nTraceback:\n{error_trace}"
            self.last_error = error_message
            self.failed_runs += 1
            scrape_successful = False
            logger.error(
                f"Critical error in scraper '{self.name}': {str(e)}\n{error_trace}"
            )

        finally:
            if not scrape_successful and not error_message:
                self.failed_runs += 1
            self.save()

    def process_article(
        self, article_url: str, scraped_article: "ScrapedArticle"
    ) -> "Article":
        """
        Full pipeline for a single article:
        1. Fetch page + extract data (1 LLM call)
        2. Rephrase title + body (1 LLM call)
        3. Create and save the Article
        """
        # Step 1: Extract
        extracted = self.extract_article_data(article_url)
        scraped_article.scraped_text = extracted["body"]

        rephrased = self.rephrase_article(extracted["title"], extracted["body"])

        final_title = rephrased.get("title") or extracted["title"]
        final_body = rephrased.get("body") or extracted["body"]

        # Truncate title if needed
        if len(final_title) > 255:
            logger.warning(f"Title truncated: {final_title[:60]}...")
            final_title = final_title[:255]

        # Step 3: POST to the target site's API to create the article
        return self.post_article_to_site(
            title=final_title,
            body=final_body,
            image_url=extracted.get("image_url"),
            image_credit=extracted.get("image_credit"),
        )

    def post_article_to_site(
        self,
        title: str,
        body: str,
        author: "Author",
        image_url: Optional[str] = None,
        image_credit: Optional[str] = None,
    ) -> dict:
        """
        POST the article data to the target site's internal API.
        Returns the response JSON from the remote API.
        """
        api_url = f"https://{self.site}/api/internal/create-article/"
        api_key = settings.INTERNAL_API_KEY

        if not api_key:
            raise Exception("INTERNAL_API_KEY env var is not set")

        payload = {
            "title": title,
            "body": body,
            "author": author.id,
            "category": self.category,
            "region": self.region.id if self.region else None,
            "image_credit": image_credit[:255] if image_credit else None,
            "image_url": image_url,  # let the receiving app download it
            "site": self.site,
        }

        try:
            response = requests.post(
                api_url,
                json=payload,
                headers={
                    "Authorization": f"Api-Key {api_key}",
                    "Content-Type": "application/json",
                },
                timeout=30,
            )
            response.raise_for_status()
            logger.info(f"Article posted to {api_url}: {title[:60]}")
            return response.json()
        except requests.HTTPError as e:
            raise Exception(
                f"API error posting article to {api_url}: {e} — {response.text[:300]}"
            )
        except requests.RequestException as e:
            raise Exception(f"Request failed posting article to {api_url}: {e}")

    def generate_image_filename(self, slug: str, article_url: str) -> str:
        upload_to_prefix = len("articles/")
        max_filename_length = 255 - upload_to_prefix
        filename_hash = hashlib.md5(article_url.encode()).hexdigest()[:8]
        max_slug_length = max_filename_length - 13
        return f"{slug[:max_slug_length]}_{filename_hash}.jpg"


class ScrapedArticle(models.Model):
    """Model to store information about articles that have been scraped."""

    url = models.URLField(unique=True, max_length=2000)
    query_params = models.TextField(
        null=True, blank=True, help_text="URL query parameters"
    )
    category = models.IntegerField()
    scraped_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=TaskStatus.choices,
        default=TaskStatus.NOT_STARTED,
    )

    scraped_text = models.TextField(null=True, blank=True)
    message = models.TextField(null=True, blank=True)
    scraper = models.ForeignKey(
        Scraper, on_delete=models.DO_NOTHING, null=True, blank=False
    )
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)
    last_retry_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.url

    @property
    def can_retry(self):
        return self.status == TaskStatus.FAILED and self.retry_count < self.max_retries

    def retry_scrape(self):
        if not self.can_retry:
            logger.warning(
                f"Cannot retry {self.url}: {self.retry_count}/{self.max_retries}"
            )
            return False

        self.retry_count += 1
        self.last_retry_at = timezone.now()
        self.status = TaskStatus.IN_PROGRESS
        self.save()

        try:
            article = self.scraper.process_article(self.url, self)
            self.article = article
            self.status = TaskStatus.SUCCESS
            self.message = None
            self.save()

            logger.info(f"Successfully retried: {self.url}")
            return True

        except Exception as e:
            error_trace = traceback.format_exc()
            self.status = TaskStatus.FAILED
            self.message = f"Retry {self.retry_count} failed: {str(e)}\n\nTraceback:\n{error_trace}"
            self.save()
            logger.error(f"Retry failed for {self.url}: {str(e)}")
            return False
