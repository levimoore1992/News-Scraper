from django.contrib import admin
from django.utils.html import format_html

from apps.scraper.models import Scraper, ScrapedArticle


@admin.register(Scraper)
class ScraperAdmin(admin.ModelAdmin):
    """Admin interface for the Scraper model."""

    list_display = (
        "name",
        "site",
        "category",
        "active",
        "last_run",
        "success_rate_display",
    )
    list_filter = ("site", "active", "category")
    search_fields = ("name", "base_url")
    readonly_fields = (
        "last_run",
        "last_success",
        "total_runs",
        "successful_runs",
        "failed_runs",
        "last_error",
    )
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "name",
                    "site",
                    "active",
                    "base_url",
                    "category",
                )
            },
        ),
        (
            "Selectors",
            {
                "fields": (
                    "section_container",
                    "article_item",
                    "href_selector",
                )
            },
        ),
        (
            "Health & Stats",
            {
                "fields": (
                    "last_run",
                    "last_success",
                    "total_runs",
                    "successful_runs",
                    "failed_runs",
                    "last_error",
                ),
            },
        ),
    )

    @admin.display(description="Success Rate")
    def success_rate_display(self, obj):
        """Displays formatted success rate colored by percentage."""
        rate = obj.success_rate
        color = "green" if rate > 80 else "orange" if rate > 50 else "red"
        return format_html('<span style="color: {};">{}%</span>', color, round(rate, 2))


@admin.register(ScrapedArticle)
class ScrapedArticleAdmin(admin.ModelAdmin):
    """Admin interface for the ScrapedArticle model."""

    list_display = (
        "url_display",
        "scraper",
        "category",
        "status",
        "scraped_at",
        "retry_count",
    )
    list_filter = ("status", "scraper_id", "category", "scraped_at")
    search_fields = ("url", "scraped_text", "message")
    readonly_fields = ("scraped_at", "last_retry_at")
    date_hierarchy = "scraped_at"

    @admin.display(description="URL")
    def url_display(self, obj):
        """Displays formatted clickable URL, truncated for length constraints."""
        # Truncate overly long URLs in display
        return format_html(
            '<a href="{}" target="_blank">{}</a>',
            obj.url,
            obj.url[:50] + "..." if len(obj.url) > 50 else obj.url,
        )
