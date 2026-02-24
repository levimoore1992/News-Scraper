import logging
import hashlib
import traceback
from tempfile import NamedTemporaryFile
from typing import Optional, List, Tuple
from urllib.parse import urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup
from django.contrib.sites.models import Site
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.files import File
from django.db import models
from slugify import slugify
from django.utils import timezone

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

    auto_publish = models.BooleanField(default=False)

    name = models.CharField(max_length=240, unique=True)

    base_url = models.CharField(max_length=1000, verbose_name="Starting url")
    section_container = models.CharField(
        max_length=240, verbose_name="Section Container", null=True, blank=True
    )
    article_item = models.CharField(
        max_length=240, verbose_name="Article Selector Path"
    )
    href_selector = models.CharField(max_length=240, verbose_name="Href selector")
    title_selector = models.CharField(max_length=240, verbose_name="Title Selector")
    text_container = models.CharField(
        max_length=240, verbose_name="Article Text Container"
    )
    text_selector = models.CharField(max_length=240, verbose_name="Text Selector")
    image_selector = models.CharField(max_length=240, verbose_name="Image Selector")
    image_credit_selector = models.CharField(
        max_length=240, verbose_name="Image Credit Selector"
    )

    
    category = models.CharField(
        max_length=240, verbose_name="Category"
    )


    # New fields for tracking scraper health
    last_run = models.DateTimeField(null=True, blank=True)
    last_success = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(null=True, blank=True)
    total_runs = models.IntegerField(default=0)
    successful_runs = models.IntegerField(default=0)
    failed_runs = models.IntegerField(default=0)

    def __str__(self):
        return self.name

    @property
    def available_authors(self):
        """Return a queryset of authors"""
        return self.region.authors

    @property
    def success_rate(self):
        """Calculate the success rate of this scraper"""
        if self.total_runs == 0:
            return 0
        return (self.successful_runs / self.total_runs) * 100

    def deactivate_scraper(self):
        """Deactivate the scraper"""
        self.active = False
        self.save()

    def parse_html(self, html_content: str) -> BeautifulSoup:
        """Parse the HTML content using BeautifulSoup."""
        return BeautifulSoup(html_content, "html.parser")

    def start_scrape(self):
        """Start the scraping process with better error handling"""
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
                self.article_url = article_url

                # Parse URL to separate base URL from query parameters
                parsed_url = urlparse(article_url)
                base_url = urlunparse(
                    (
                        parsed_url.scheme,
                        parsed_url.netloc,
                        parsed_url.path,
                        "",  # params
                        "",  # query - removed
                        "",  # fragment
                    )
                )

                # Extract query parameters
                query_params = parsed_url.query if parsed_url.query else None

                # Check if article already exists using base URL (without query params)
                if ScrapedArticle.objects.filter(url=base_url).exists():
                    continue  # Skip if article already exists

                scraped_article = ScrapedArticle(
                    status=TaskStatus.IN_PROGRESS,
                    url=base_url,
                    query_params=query_params,
                    category=self.category,
                    scraper=self,
                )

                try:
                    self.scrape_article_components()
                    scraped_article.scraped_text = self.body
                    scraped_article.status = TaskStatus.SUCCESS
                    article = self.create_article(self.category)
                    scraped_article.article = article
                    article.save()
                    scraped_article.save()

                    if self.auto_publish:
                        article.publish()

                    logger.info(f"Successfully scraped: {article_url}")

                except Exception as e:
                    error_trace = traceback.format_exc()
                    scraped_article.status = TaskStatus.FAILED
                    scraped_article.message = f"{str(e)}\n\nTraceback:\n{error_trace}"
                    scraped_article.retry_count = 0
                    scraped_article.save()

                    logger.error(
                        f"Error scraping article {article_url}: {str(e)}\n{error_trace}"
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

    def fetch_page(self, url: str) -> Optional[str]:
        """Fetch the HTML content of the given URL with proper headers."""
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

        # Check for Playwright fallback flag
        if getattr(self, "_use_playwright", False):
            return self._fetch_with_playwright(url)

        try:
            response = requests.get(
                url, headers=headers, timeout=30, allow_redirects=True
            )
            response.raise_for_status()
            return response.text
        except requests.Timeout as e:
            logger.error(f"Timeout fetching {url}: {str(e)}")
            raise Exception(f"Timeout fetching {url}: {str(e)}")
        except requests.ConnectionError as e:
            logger.error(f"Connection error fetching {url}: {str(e)}")
            raise Exception(f"Connection error fetching {url}: {str(e)}")
        except requests.HTTPError as e:
            status_code = response.status_code if "response" in locals() else "unknown"
            error_msg = f"HTTP error {status_code} fetching {url}: {str(e)}"

            # Add specific guidance for 403 errors
            if status_code == 403:
                error_msg += " (Website is blocking the request - may need different scraping approach)"

            logger.error(error_msg)
            raise Exception(error_msg)
        except requests.RequestException as e:
            logger.error(f"Error fetching {url}: {str(e)}")
            raise Exception(f"Error fetching {url}: {str(e)}")

    def _fetch_with_playwright(self, url: str) -> str:
        """Fetch page content using Playwright with headless shell"""
        try:
            with sync_playwright() as p:
                try:
                    # Just use 'chromium' - Playwright will automatically use the headless shell
                    # if that's all that's available (which it is after your post_compile cleanup)
                    browser = p.chromium.launch(
                        headless=True,
                        args=[
                            "--no-sandbox",
                            "--disable-setuid-sandbox",
                            "--disable-dev-shm-usage",
                            "--disable-gpu",
                        ],
                    )
                except Exception as e:
                    logger.error(f"Failed to launch Playwright browser: {e}")
                    logger.error(
                        "Playwright headless shell may not be properly installed."
                    )
                    raise Exception(f"Playwright browser launch failed: {e}")

                # Use a realistic User-Agent
                ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                context = browser.new_context(user_agent=ua)
                page = context.new_page()
                try:
                    page.goto(url, timeout=60000, wait_until="domcontentloaded")
                    content = page.content()
                    return content
                except Exception as e:
                    logger.error(f"Playwright error processing {url}: {e}")
                    raise e
                finally:
                    browser.close()
        except ImportError as e:
            logger.error(f"Playwright import error: {e}")
            raise Exception(
                "Playwright is not installed. Add 'playwright' to requirements.txt"
            )

    def try_selectors(
        self, soup: BeautifulSoup, selector_string: str, select_all=False
    ):
        """
        Try multiple selectors separated by comma until one matches.

        Args:
            soup: BeautifulSoup object
            selector_string: Comma-separated string of CSS selectors
            select_all: If True, use select() instead of select_one()

        Returns:
            The first matching element(s) or None
        """
        selectors = [s.strip() for s in selector_string.split(",") if s.strip()]

        for selector in selectors:
            try:
                if select_all:
                    result = soup.select(selector)
                    if result:
                        return result
                else:
                    result = soup.select_one(selector)
                    if result:
                        return result
            except Exception as e:
                logger.debug(f"Selector '{selector}' failed: {e}")
                continue

        return None

    def scrape_section(self) -> List[str]:
        """Scrape a specific section to get the URLs of articles."""
        attempts = [False, True]
        last_error = None

        for use_pw in attempts:
            self._use_playwright = use_pw
            try:
                article_urls = []
                section_page = self.fetch_page(self.base_url)
                if section_page:
                    soup = self.parse_html(section_page)
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
                        raise Exception(
                            f"No items found with selector '{self.article_item}'"
                        )

                    for item in items:
                        href_elem = item.select_one(self.href_selector)
                        if href_elem and href_elem.has_attr("href"):
                            full_url = urljoin(self.base_url, href_elem["href"])
                            article_urls.append(full_url)

                # If we successfully got article URLs, return them
                if article_urls:
                    if use_pw:
                        logger.info("Successfully scraped section using Playwright")
                    return article_urls
                else:
                    raise Exception("No article URLs found after processing items")

            except Exception as e:
                last_error = e
                if not use_pw:
                    logger.info(
                        f"Standard scrape failed for section, retrying with Playwright: {e}"
                    )
                    continue
                else:
                    # Both attempts failed, raise the last error
                    logger.error(f"Both scrape attempts failed for section: {e}")
                    raise e

        # If we get here, both attempts failed
        if last_error:
            raise last_error
        return []

    def scrape_article_components(self):
        """Scrape article components such as title, body, and image."""
        attempts = [False, True]
        last_error = None

        for use_pw in attempts:
            self._use_playwright = use_pw
            try:
                self.title = self.scrape_title()
                if not self.title:
                    raise Exception(f"Failed to extract title from {self.article_url}")

                self.body = self.get_complete_article_text()
                if not self.body:
                    raise Exception(
                        f"Failed to extract body text from {self.article_url}"
                    )

                self.image, self.image_credit = self.get_article_image()

                # If we got here, scraping was successful
                if use_pw:
                    logger.info(
                        f"Successfully scraped article using Playwright: {self.article_url}"
                    )
                return  # Scrape successful

            except Exception as e:
                last_error = e
                if not use_pw:
                    logger.info(
                        f"Standard scrape failed for article {self.article_url}, retrying with Playwright: {e}"
                    )
                    continue
                else:
                    # Both attempts failed
                    logger.error(f"Both scrape attempts failed for article: {e}")
                    raise e

        # If we get here, both attempts failed
        if last_error:
            raise last_error

    def scrape_title(self) -> Optional[str]:
        """Scrape an article and extract the title."""
        article_page = self.fetch_page(self.article_url)
        if article_page:
            soup = self.parse_html(article_page)
            title_elem = self.try_selectors(soup, self.title_selector)
            if title_elem:
                return title_elem.get_text().strip()
        return None

    def get_complete_article_text(self) -> Optional[str]:
        """Scrape an article and extract all the text within specified tags."""
        article_page = self.fetch_page(self.article_url)
        if article_page:
            soup = self.parse_html(article_page)
            story_container = self.try_selectors(soup, self.text_container)
            if story_container:
                paragraphs = self.try_selectors(
                    story_container, self.text_selector, select_all=True
                )
                if paragraphs:
                    return " ".join(p.get_text().strip() for p in paragraphs)
        return None

    def get_article_image(self) -> Tuple[Optional[str], Optional[str]]:
        """Scrape an article and extract the image and its credit."""
        image, image_credit = None, None
        article_page = self.fetch_page(self.article_url)
        if article_page:
            soup = self.parse_html(article_page)
            image_elem = soup.select_one(self.image_selector)
            if image_elem:
                # Check for 'data-src' attribute first (common for lazy-loaded images)
                image = image_elem.get("data-src") or image_elem.get("src")

                # If it's still a data URI, try to find a different image
                if image and image.startswith("data:"):
                    # Look for other image elements that might have a valid URL
                    all_images = soup.select("img")
                    for img in all_images:
                        potential_src = img.get("data-src") or img.get("src")
                        if potential_src and not potential_src.startswith("data:"):
                            image = potential_src
                            break

                if image and not image.startswith("data:"):
                    # Ensure the image URL is absolute
                    image = urljoin(self.article_url, image)
                else:
                    image = None

            image_credit_elem = soup.select_one(self.image_credit_selector)
            if image_credit_elem:
                image_credit = image_credit_elem.get_text().strip()

        return image, image_credit

    def create_article(self, category: Category) -> Article:
        if not (self.title and self.body):
            logger.error(
                f"Missing title or body: title='{self.title}', body_length={len(self.body) if self.body else 0}"
            )
            raise Exception(f"Missing title or body: {self.title}, {self.body}")

        try:
            author = (
                self.available_authors.order_by("?").first()
                if self.available_authors
                else Author.objects.order_by("?").first()
            )

            rephrased_title = self.rephrase_title() or self.title
            rephrased_body = self.rephrase_body(author.writing_style) or self.body

            # Truncate title if necessary
            max_title_length = 255
            if len(rephrased_title) > max_title_length:
                original_title = rephrased_title
                rephrased_title = rephrased_title[:max_title_length]
                logger.warning(
                    f"Title truncated from {len(original_title)} to {len(rephrased_title)} characters"
                )


            article = Article(
                title=rephrased_title,
                body=rephrased_body,
                author=author,
                category=category,
                region=self.region,
                image_credit=self.image_credit[:255] if self.image_credit else None,
            )

            if self.image:
                try:
                    img_temp = NamedTemporaryFile(delete=True)
                    img_response = requests.get(self.image, timeout=10)
                    img_response.raise_for_status()
                    img_temp.write(img_response.content)
                    img_temp.flush()

                    image_filename = self.generate_image_filename(slugify(rephrased_title))

                    article.image.save(image_filename, File(img_temp))
                except requests.RequestException as e:
                    logger.error(f"Error processing image {self.image}: {e}")
                    article.image = None
                    article.image_credit = None

            article.full_clean()

            article.save()

            if self.site:
                article.sites.add(self.site)

            return article
        except (ObjectDoesNotExist, ValidationError) as e:
            logger.error(f"Error creating article: {str(e)}", exc_info=True)
            raise

    def rephrase_title(self):
        """Rephrase the title using the AI Model we have"""
        prompt = f"Rephrase the following title: {self.title}. Be short and dont explain. Just respond"
        return self.chat_model.send_prompt(prompt)

    def rephrase_body(self, style) -> str:
        """
        Rephrase and convert the given body text to HTML using the AI model we have.
        """
        prompt = f"""
        In HTML format only using p tags rephrase the following text {self.body}
        with the writing style of {style if style else 'a unbiased journalist'} with a strong mix of tabloid / viral BuzzFeed style.
        Make sure each new paragraph is wrapped in a p tag. There must be at least 5 paragraphs wrapped in p tags.
        Write it in a way that the first paragraph is a huge cliff hanger."""

        return self.chat_model.send_prompt(prompt)

    def generate_image_filename(self, slug: str) -> str:
        """
        Generate a unique filename for the article image.
        Must account for the upload_to prefix 'articles/' (9 chars)
        so filename itself can only be 246 chars max.
        """
        upload_to_prefix = len("articles/")  # 9 chars
        max_filename_length = 255 - upload_to_prefix  # 246 chars

        filename_hash = hashlib.md5(self.article_url.encode()).hexdigest()[:8]
        # hash(8) + underscore(1) + .jpg(4) = 13 chars reserved
        max_slug_length = max_filename_length - 13

        slug_prefix = slug[:max_slug_length]
        filename = f"{slug_prefix}_{filename_hash}.jpg"

        logger.info(f"Generated image filename: {filename} ({len(filename)} chars)")
        return filename


class ScrapedArticle(models.Model):
    """
    Model to store information about articles that have been scraped.
    """

    url = models.URLField(unique=True, max_length=2000)
    query_params = models.TextField(
        null=True, blank=True, help_text="URL query parameters"
    )
    category = models.ForeignKey("Category", on_delete=models.CASCADE)
    scraped_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=TaskStatus.choices,
        default=TaskStatus.NOT_STARTED,
    )
    article = models.OneToOneField(
        "Article", on_delete=models.SET_NULL, null=True, blank=True
    )
    scraped_text = models.TextField(null=True, blank=True)
    message = models.TextField(null=True, blank=True)

    scraper = models.ForeignKey(
        Scraper, on_delete=models.DO_NOTHING, null=True, blank=False
    )

    # New fields for retry functionality
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)
    last_retry_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.url}"

    @property
    def can_retry(self):
        """Check if this article can be retried"""
        return self.status == TaskStatus.FAILED and self.retry_count < self.max_retries

    def retry_scrape(self):
        """Retry scraping this article"""
        if not self.can_retry:
            logger.warning(
                f"Cannot retry {self.url}: retry_count={self.retry_count}, max_retries={self.max_retries}"
            )
            return False

        self.retry_count += 1
        self.last_retry_at = timezone.now()
        self.status = TaskStatus.IN_PROGRESS
        self.save()

        try:
            scraper = self.scraper
            scraper.article_url = self.url
            scraper.scrape_article_components()

            self.scraped_text = scraper.body
            self.status = TaskStatus.SUCCESS
            self.message = None  # Clear previous error message
            article = scraper.create_article(self.category)
            self.article = article
            article.save()
            self.save()

            if scraper.auto_publish:
                article.publish()

            logger.info(f"Successfully retried scraping: {self.url}")
            return True

        except Exception as e:
            error_trace = traceback.format_exc()
            self.status = TaskStatus.FAILED
            self.message = f"Retry {self.retry_count} failed: {str(e)}\n\nTraceback:\n{error_trace}"
            self.save()

            logger.error(f"Retry failed for {self.url}: {str(e)}\n{error_trace}")

            return False
