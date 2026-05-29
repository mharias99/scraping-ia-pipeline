import argparse
import asyncio
import logging
import time
from pathlib import Path

from scraper.quotes_scraper import run_scraper, save_raw
from cleaner.enricher import run_enricher

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pipeline: Scraping + IA enrichment")
    parser.add_argument(
        "--pages",
        type=int,
        default=5,
        help="Max pages to scrape (default: 5)",
    )
    parser.add_argument(
        "--skip-scrape",
        action="store_true",
        help="Skip scraping and use existing data/raw/ file",
    )
    parser.add_argument(
        "--skip-enrich",
        action="store_true",
        help="Skip enrichment (only scrape)",
    )
    return parser.parse_args()


def run_pipeline(pages: int, skip_scrape: bool, skip_enrich: bool) -> None:
    start = time.perf_counter()
    raw_path = Path("data/raw/quotes_raw.json")

    # ── Step 1: Scraping ────────────────────────────────────────────────────
    if skip_scrape:
        if not raw_path.exists():
            raise FileNotFoundError(
                f"--skip-scrape set but no raw data found at {raw_path}"
            )
        logger.info("Step 1/2 skipped — using existing %s", raw_path)
    else:
        logger.info("Step 1/2 — Scraping (max %d pages)...", pages)
        quotes = asyncio.run(run_scraper(max_pages=pages))
        if not quotes:
            raise RuntimeError("Scraper returned no data. Aborting pipeline.")
        save_raw(quotes)
        logger.info("Step 1/2 done — %d quotes saved to %s", len(quotes), raw_path)

    # ── Step 2: Enrichment ──────────────────────────────────────────────────
    if skip_enrich:
        logger.info("Step 2/2 skipped — enrichment disabled.")
    else:
        logger.info("Step 2/2 — Enriching with Claude API...")
        output_path = run_enricher()
        elapsed = time.perf_counter() - start
        logger.info("Pipeline complete in %.1fs — output: %s", elapsed, output_path)
        return

    elapsed = time.perf_counter() - start
    logger.info("Pipeline complete in %.1fs", elapsed)


if __name__ == "__main__":
    args = parse_args()
    run_pipeline(
        pages=args.pages,
        skip_scrape=args.skip_scrape,
        skip_enrich=args.skip_enrich,
    )
