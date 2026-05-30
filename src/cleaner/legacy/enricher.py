import json
import logging
import os
import time
from pathlib import Path
from typing import Any

import anthropic
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

RAW_PATH = Path("data/raw/quotes_raw.json")
OUTPUT_DIR = Path("data/output")
BATCH_SIZE = 10
MAX_RETRIES = 3

ENRICH_TOOL = {
    "name": "enrich_quotes",
    "description": "Enriches a batch of quotes with semantic metadata.",
    "input_schema": {
        "type": "object",
        "properties": {
            "quotes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "index": {"type": "integer", "description": "Original index of the quote in the batch"},
                        "category": {
                            "type": "string",
                            "enum": ["philosophy", "inspiration", "humor", "life", "knowledge", "love", "other"],
                            "description": "Main thematic category",
                        },
                        "sentiment": {
                            "type": "string",
                            "enum": ["positive", "negative", "neutral"],
                            "description": "Emotional tone of the quote",
                        },
                        "key_themes": {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 1,
                            "maxItems": 3,
                            "description": "2-3 semantic themes, more abstract than tags",
                        },
                        "complexity": {
                            "type": "string",
                            "enum": ["simple", "moderate", "complex"],
                            "description": "Language and conceptual complexity",
                        },
                    },
                    "required": ["index", "category", "sentiment", "key_themes", "complexity"],
                },
            }
        },
        "required": ["quotes"],
    },
}


def load_raw_data(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Raw data not found: {path}")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not data:
        raise ValueError("Raw data file is empty.")
    logger.info("Loaded %d records from %s", len(data), path)
    return data


def build_prompt(batch: list[dict[str, Any]]) -> str:
    lines = []
    for i, q in enumerate(batch):
        lines.append(f"[{i}] \"{q['text']}\" — {q['author']} | tags: {', '.join(q.get('tags') or [])}")
    return "Analyze and enrich the following quotes:\n\n" + "\n".join(lines)


def enrich_batch(
    client: anthropic.Anthropic,
    batch: list[dict[str, Any]],
    attempt: int = 1,
) -> list[dict[str, Any]]:
    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            tools=[ENRICH_TOOL],
            tool_choice={"type": "tool", "name": "enrich_quotes"},
            messages=[{"role": "user", "content": build_prompt(batch)}],
        )

        tool_block = next(
            (b for b in response.content if b.type == "tool_use"),
            None,
        )
        if not tool_block:
            raise ValueError("No tool_use block in response.")

        enriched: list[dict[str, Any]] = tool_block.input["quotes"]
        return enriched

    except anthropic.RateLimitError:
        if attempt > MAX_RETRIES:
            logger.error("Rate limit exceeded after %d retries. Skipping batch.", MAX_RETRIES)
            return []
        wait = 2 ** attempt
        logger.warning("Rate limit hit. Retrying in %ds (attempt %d/%d)...", wait, attempt, MAX_RETRIES)
        time.sleep(wait)
        return enrich_batch(client, batch, attempt + 1)

    except anthropic.BadRequestError as e:
        if "credit balance is too low" in str(e):
            raise RuntimeError(
                "Anthropic API: insufficient credits. "
                "Add funds at https://console.anthropic.com/settings/billing"
            ) from e
        logger.error("Bad request to Anthropic API: %s", e)
        raise

    except anthropic.APIError as e:
        logger.error("Anthropic API error on batch: %s", type(e).__name__)
        raise


def merge_results(
    raw: list[dict[str, Any]],
    enriched: list[dict[str, Any]],
    batch_offset: int,
) -> list[dict[str, Any]]:
    merged = []
    enriched_by_index = {e["index"]: e for e in enriched}
    for i, record in enumerate(raw):
        meta = enriched_by_index.get(i)
        if not meta:
            logger.warning("Missing enrichment for batch index %d (global %d)", i, batch_offset + i)
            continue
        raw_themes = meta.get("key_themes") or []
        merged.append({
            "text": record["text"],
            "author": record["author"],
            "tags": ", ".join(record.get("tags") or []),
            "category": meta.get("category", "other"),
            "sentiment": meta.get("sentiment", "neutral"),
            "key_themes": ", ".join(raw_themes if isinstance(raw_themes, list) else [str(raw_themes)]),
            "complexity": meta.get("complexity", "moderate"),
        })
    return merged


def build_dataframe(records: list[dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(records)
    df.drop_duplicates(subset=["text"], inplace=True)
    for col in ["author", "category", "sentiment", "complexity"]:
        df[col] = df[col].str.strip().str.lower()
    df.reset_index(drop=True, inplace=True)
    return df


def save_csv(df: pd.DataFrame) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    from datetime import date
    filename = f"dataset_{date.today().strftime('%Y%m%d')}.csv"
    output_path = OUTPUT_DIR / filename
    df.to_csv(output_path, index=False, encoding="utf-8")
    logger.info("CSV exported: %s (%d rows, %d cols)", output_path, len(df), len(df.columns))
    return output_path


def run_enricher() -> Path:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY not set in environment.")

    client = anthropic.Anthropic(api_key=api_key)
    raw_data = load_raw_data(RAW_PATH)

    all_records: list[dict[str, Any]] = []
    batches = [raw_data[i : i + BATCH_SIZE] for i in range(0, len(raw_data), BATCH_SIZE)]

    for batch_num, batch in enumerate(batches, start=1):
        logger.info("Enriching batch %d/%d (%d quotes)...", batch_num, len(batches), len(batch))
        enriched = enrich_batch(client, batch)
        if enriched:
            records = merge_results(batch, enriched, batch_offset=(batch_num - 1) * BATCH_SIZE)
            all_records.extend(records)
            logger.info("  -> %d records merged (total: %d)", len(records), len(all_records))
        time.sleep(0.5)

    if not all_records:
        raise RuntimeError("No records were enriched successfully.")

    df = build_dataframe(all_records)
    return save_csv(df)


if __name__ == "__main__":
    output = run_enricher()
    logger.info("Pipeline complete. Output: %s", output)
