import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class ApifyConfig:
    enabled: bool = False
    actor_infojobs: str = "unfenced-group/infojobs-net-scraper"
    actor_indeed: str = "misceres/indeed-scraper"
    max_items_per_query: int = 50
    infojobs_queries: list[str] = field(default_factory=list)
    indeed_queries: list[str] = field(default_factory=list)


@dataclass
class ScraperConfig:
    # "firecrawl" | "apify" | "both" | "milanuncios" | "gmaps"
    source: str = "firecrawl"
    location: str = "España"
    queries: list[str] = field(default_factory=list)
    infojobs_queries: list[str] = field(default_factory=list)
    indeed_queries: list[str] = field(default_factory=list)
    max_pages_per_query: int = 3
    max_results: int = 30
    apify: ApifyConfig = field(default_factory=ApifyConfig)


@dataclass
class CarScraperConfig:
    car_models: list[str] = field(default_factory=list)
    max_results_per_model: int = 50
    price_min: int = 1000
    price_max: int = 30000
    seller_type: str = "private"
    arbitrage_threshold: float = 0.15   # 15% por debajo de la mediana = HIGH


@dataclass
class GmapsScraperConfig:
    search_queries: list[str] = field(default_factory=list)
    location: str = "Madrid"
    max_results_per_query: int = 30
    language: str = "es"


@dataclass
class EnricherConfig:
    model: str = "claude-haiku-4-5-20251001"
    batch_size: int = 5
    min_score: str = "low"


@dataclass
class SheetsConfig:
    enabled: bool = True
    spreadsheet_id: str = ""
    worksheet_name: str = "Leads"


@dataclass
class DeliveryConfig:
    google_sheets: SheetsConfig = field(default_factory=SheetsConfig)


@dataclass
class PipelineConfig:
    # "b2b_leads" | "car_arbitrage" | "digital_audit"
    pipeline_type: str = "b2b_leads"
    client_name: str = "default"
    client_id: str = "default"
    scraper: ScraperConfig = field(default_factory=ScraperConfig)
    car_scraper: CarScraperConfig = field(default_factory=CarScraperConfig)
    gmaps_scraper: GmapsScraperConfig = field(default_factory=GmapsScraperConfig)
    enricher: EnricherConfig = field(default_factory=EnricherConfig)
    delivery: DeliveryConfig = field(default_factory=DeliveryConfig)


def load_config(path: str | Path) -> PipelineConfig:
    with open(path, encoding="utf-8") as f:
        raw: dict[str, Any] = yaml.safe_load(f)

    client        = raw.get("client", {})
    scraper       = raw.get("scraper", {})
    car_scraper   = raw.get("car_scraper", {})
    gmaps_scraper = raw.get("gmaps_scraper", {})
    enricher      = raw.get("enricher", {})
    delivery      = raw.get("delivery", {})
    sheets        = delivery.get("google_sheets", {})
    apify_raw     = scraper.get("apify", {})

    spreadsheet_id = sheets.get("spreadsheet_id") or os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID", "")

    return PipelineConfig(
        pipeline_type=raw.get("pipeline_type", "b2b_leads"),
        client_name=client.get("name", "default"),
        client_id=client.get("id", "default"),
        scraper=ScraperConfig(
            source=scraper.get("source", "firecrawl"),
            location=scraper.get("location", "España"),
            queries=scraper.get("queries", []),
            infojobs_queries=scraper.get("infojobs_queries", []),
            indeed_queries=scraper.get("indeed_queries", []),
            max_pages_per_query=scraper.get("max_pages_per_query", 3),
            max_results=scraper.get("max_results", 30),
            apify=ApifyConfig(
                enabled=apify_raw.get("enabled", False),
                actor_infojobs=apify_raw.get("actor_infojobs", "unfenced-group/infojobs-net-scraper"),
                actor_indeed=apify_raw.get("actor_indeed", "misceres/indeed-scraper"),
                max_items_per_query=apify_raw.get("max_items_per_query", 50),
                infojobs_queries=apify_raw.get("infojobs_queries", []),
                indeed_queries=apify_raw.get("indeed_queries", []),
            ),
        ),
        car_scraper=CarScraperConfig(
            car_models=car_scraper.get("car_models", []),
            max_results_per_model=car_scraper.get("max_results_per_model", 50),
            price_min=car_scraper.get("price_min", 1000),
            price_max=car_scraper.get("price_max", 30000),
            seller_type=car_scraper.get("seller_type", "private"),
            arbitrage_threshold=car_scraper.get("arbitrage_threshold", 0.15),
        ),
        gmaps_scraper=GmapsScraperConfig(
            search_queries=gmaps_scraper.get("search_queries", []),
            location=gmaps_scraper.get("location", "Madrid"),
            max_results_per_query=gmaps_scraper.get("max_results_per_query", 30),
            language=gmaps_scraper.get("language", "es"),
        ),
        enricher=EnricherConfig(
            model=enricher.get("model", "claude-haiku-4-5-20251001"),
            batch_size=enricher.get("batch_size", 5),
            min_score=enricher.get("min_score", "low"),
        ),
        delivery=DeliveryConfig(
            google_sheets=SheetsConfig(
                enabled=sheets.get("enabled", True),
                spreadsheet_id=spreadsheet_id,
                worksheet_name=sheets.get("worksheet_name", "Leads"),
            )
        ),
    )
