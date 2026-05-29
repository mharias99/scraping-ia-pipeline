import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class ScraperConfig:
    source: str = "indeed"
    location: str = "España"
    queries: list[str] = field(default_factory=list)
    max_pages_per_query: int = 3
    max_results: int = 30


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
    client_name: str = "default"
    client_id: str = "default"
    scraper: ScraperConfig = field(default_factory=ScraperConfig)
    enricher: EnricherConfig = field(default_factory=EnricherConfig)
    delivery: DeliveryConfig = field(default_factory=DeliveryConfig)


def load_config(path: str | Path) -> PipelineConfig:
    with open(path, encoding="utf-8") as f:
        raw: dict[str, Any] = yaml.safe_load(f)

    client  = raw.get("client", {})
    scraper = raw.get("scraper", {})
    enricher = raw.get("enricher", {})
    delivery = raw.get("delivery", {})
    sheets  = delivery.get("google_sheets", {})

    # spreadsheet_id: config > .env
    spreadsheet_id = sheets.get("spreadsheet_id") or os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID", "")

    return PipelineConfig(
        client_name=client.get("name", "default"),
        client_id=client.get("id", "default"),
        scraper=ScraperConfig(
            source=scraper.get("source", "indeed"),
            location=scraper.get("location", "España"),
            queries=scraper.get("queries", []),
            max_pages_per_query=scraper.get("max_pages_per_query", 3),
            max_results=scraper.get("max_results", 30),
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
