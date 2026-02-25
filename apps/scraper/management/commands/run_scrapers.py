import concurrent.futures
from django.core.management.base import BaseCommand
from django.db import close_old_connections
from apps.scraper.models import Scraper


class Command(BaseCommand):
    """Management command to start scraping tasks concurrently."""

    help = "Efficiently runs all active scrapers or a specific scraper concurrently."

    def add_arguments(self, parser):
        parser.add_argument(
            "--scraper-id",
            type=int,
            help="ID of a specific scraper to run",
        )
        parser.add_argument(
            "--workers",
            type=int,
            default=3,
            help="Number of concurrent workers (default: 3)",
        )

    def handle(self, *args, **options):
        scraper_id = options.get("scraper_id")
        workers = options.get("workers", 3)

        if scraper_id:
            scrapers = Scraper.objects.filter(id=scraper_id, active=True)
        else:
            scrapers = Scraper.objects.filter(active=True)

        if not scrapers.exists():
            self.stdout.write(self.style.WARNING("No active scrapers found."))
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"Starting {scrapers.count()} scraper(s) with {workers} worker(s)..."
            )
        )

        def run_scraper(scraper):
            close_old_connections()
            self.stdout.write(f"Starting scraper: {scraper.name}")
            try:
                scraper.start_scrape()
                self.stdout.write(
                    self.style.SUCCESS(f"Finished scraper: {scraper.name}")
                )
            except Exception as e:  # pylint: disable=broad-exception-caught
                self.stdout.write(
                    self.style.ERROR(f"Error in scraper {scraper.name}: {e}")
                )
            finally:
                close_old_connections()

        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            executor.map(run_scraper, scrapers)

        self.stdout.write(self.style.SUCCESS("All scraping tasks completed."))
