import json
import logging
import os
import re
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

RAW_PATH    = Path("data/raw/indeed_raw.json")
OUTPUT_DIR  = Path("data/output")
BATCH_SIZE  = 5   # descripciones largas → batches pequeños
MAX_RETRIES = 3

# ── Regex LOPD: emails personales a filtrar ───────────────────────────────────
PERSONAL_EMAIL_DOMAINS = re.compile(
    r"@(gmail|hotmail|yahoo|outlook|live|icloud|me|msn|terra|telefonica|wanadoo"
    r"|orange|vodafone|ono|jazztel|masmovil|protonmail|tutanota)\.",
    re.IGNORECASE,
)


# ── JSON Schema para lead qualification ──────────────────────────────────────
#
# Campos que Claude devuelve por cada oferta analizada:
#
#   index              int     — índice en el batch (0-based)
#   is_lead            bool    — True si la empresa es candidata a automatización
#   lead_score         enum    — "high" | "medium" | "low" | "discard"
#   lead_reason        str     — 1 frase explicando por qué es (o no) lead
#   automation_signals list    — señales detectadas: ["data entry manual", "excel reporting", ...]
#   company_sector     str     — sector estimado: "logística", "contabilidad", "retail"...
#   company_size       enum    — "micro" | "small" | "medium" | "large" | "unknown"
#   urgency            enum    — "urgent" | "normal" | "unknown"
#   contact_email      str|null — solo corporativo (LOPD); null si es personal o no encontrado

LEAD_TOOL = {
    "name": "qualify_leads",
    "description": (
        "Analyzes job offers and qualifies them as B2B automation leads. "
        "A HIGH lead is a company trying to hire a human to manually do data entry, "
        "Excel management, or administrative backoffice tasks — ideal targets for selling "
        "backoffice automation services."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "leads": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "index": {"type": "integer"},
                        "is_lead": {
                            "type": "boolean",
                            "description": "True if the company is a valid automation lead",
                        },
                        "lead_score": {
                            "type": "string",
                            "enum": ["high", "medium", "low", "discard"],
                            "description": (
                                "high: explicitly hiring for manual data entry/Excel tasks. "
                                "medium: admin role with significant Excel/data component. "
                                "low: mentions Excel but not the core task. "
                                "discard: no automation opportunity detected."
                            ),
                        },
                        "lead_reason": {
                            "type": "string",
                            "description": "One sentence explaining the lead score in Spanish",
                        },
                        "automation_signals": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Exact phrases from the job description signaling manual work",
                        },
                        "company_sector": {
                            "type": "string",
                            "description": "Estimated business sector in Spanish (e.g. logística, contabilidad)",
                        },
                        "company_size": {
                            "type": "string",
                            "enum": ["micro", "small", "medium", "large", "unknown"],
                        },
                        "urgency": {
                            "type": "string",
                            "enum": ["urgent", "normal", "unknown"],
                            "description": "urgent if job post mentions 'incorporación inmediata' or similar",
                        },
                        "contact_email": {
                            "type": ["string", "null"],
                            "description": "Corporate email only. null if personal domain or not found (LOPD)",
                        },
                    },
                    "required": [
                        "index", "is_lead", "lead_score", "lead_reason",
                        "automation_signals", "company_sector", "company_size",
                        "urgency", "contact_email",
                    ],
                },
            }
        },
        "required": ["leads"],
    },
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def sanitize_email_lopd(email: str | None) -> str | None:
    if not email:
        return None
    if PERSONAL_EMAIL_DOMAINS.search(email):
        logger.info("LOPD: email personal eliminado (%s)", email.split("@")[1])
        return None
    return email


def build_lead_prompt(batch: list[dict[str, Any]]) -> str:
    lines = ["Analyze each job offer and qualify it as a B2B backoffice automation lead.\n"]
    for i, job in enumerate(batch):
        lines.append(f"--- OFERTA [{i}] ---")
        lines.append(f"Título: {job.get('title', '')}")
        lines.append(f"Empresa: {job.get('company', '')}")
        lines.append(f"Ubicación: {job.get('location', '')}")
        lines.append(f"Descripción: {job.get('description', '')[:1200]}")
        lines.append(f"Requisitos: {job.get('requirements', '')[:600]}")
        lines.append("")
    return "\n".join(lines)


def enrich_batch(
    client: anthropic.Anthropic,
    batch: list[dict[str, Any]],
    attempt: int = 1,
) -> list[dict[str, Any]]:
    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2048,
            tools=[LEAD_TOOL],
            tool_choice={"type": "tool", "name": "qualify_leads"},
            messages=[{"role": "user", "content": build_lead_prompt(batch)}],
        )
        tool_block = next((b for b in response.content if b.type == "tool_use"), None)
        if not tool_block:
            raise ValueError("No tool_use block in response.")
        return tool_block.input["leads"]

    except anthropic.RateLimitError:
        if attempt > MAX_RETRIES:
            logger.error("Rate limit: max retries alcanzado. Saltando batch.")
            return []
        wait = 2 ** attempt
        logger.warning("Rate limit. Reintentando en %ds...", wait)
        time.sleep(wait)
        return enrich_batch(client, batch, attempt + 1)

    except anthropic.BadRequestError as e:
        if "credit balance is too low" in str(e):
            raise RuntimeError(
                "Anthropic API: saldo insuficiente. "
                "Recarga en https://console.anthropic.com/settings/billing"
            ) from e
        logger.error("BadRequestError: %s", e)
        raise

    except anthropic.APIError as e:
        logger.error("APIError: %s", type(e).__name__)
        raise


def merge_results(
    raw: list[dict[str, Any]],
    enriched: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    enriched_map = {e["index"]: e for e in enriched}
    merged = []
    for i, job in enumerate(raw):
        meta = enriched_map.get(i)
        if not meta:
            logger.warning("Sin enriquecimiento para índice %d", i)
            continue
        merged.append({
            # Datos crudos
            "title":             job.get("title", ""),
            "company":           job.get("company", ""),
            "location":          job.get("location", ""),
            "salary":            job.get("salary", ""),
            "url":               job.get("url", ""),
            "query":             job.get("query", ""),
            "scraped_at":        job.get("scraped_at", ""),
            # Enriquecimiento IA
            "is_lead":           meta["is_lead"],
            "lead_score":        meta["lead_score"],
            "lead_reason":       meta["lead_reason"],
            "automation_signals": ", ".join(meta.get("automation_signals", [])),
            "company_sector":    meta["company_sector"],
            "company_size":      meta["company_size"],
            "urgency":           meta["urgency"],
            # LOPD: sanitizado
            "contact_email":     sanitize_email_lopd(meta.get("contact_email")),
        })
    return merged


def build_dataframe(records: list[dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(records)
    df.drop_duplicates(subset=["url"], inplace=True)
    for col in ["company", "company_sector", "location"]:
        if col in df.columns:
            df[col] = df[col].str.strip().str.lower()
    df.sort_values("lead_score", key=lambda s: s.map(
        {"high": 0, "medium": 1, "low": 2, "discard": 3}
    ), inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


def save_csv(df: pd.DataFrame) -> Path:
    from datetime import date
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / f"leads_{date.today().strftime('%Y%m%d')}.csv"
    df.to_csv(path, index=False, encoding="utf-8")
    logger.info("CSV exportado: %s (%d leads, %d cols)", path, len(df), len(df.columns))
    return path


def run_lead_enricher() -> Path:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY no encontrada en el entorno.")

    client = anthropic.Anthropic(api_key=api_key)

    if not RAW_PATH.exists():
        raise FileNotFoundError(f"No hay datos crudos en {RAW_PATH}. Ejecuta primero el scraper.")
    with open(RAW_PATH, encoding="utf-8") as f:
        raw_data: list[dict[str, Any]] = json.load(f)
    if not raw_data:
        raise ValueError("El archivo de datos crudos está vacío.")
    logger.info("%d ofertas cargadas desde %s", len(raw_data), RAW_PATH)

    all_records: list[dict[str, Any]] = []
    batches = [raw_data[i: i + BATCH_SIZE] for i in range(0, len(raw_data), BATCH_SIZE)]

    for n, batch in enumerate(batches, start=1):
        logger.info("Batch %d/%d (%d ofertas)...", n, len(batches), len(batch))
        enriched = enrich_batch(client, batch)
        if enriched:
            records = merge_results(batch, enriched)
            all_records.extend(records)
            high = sum(1 for r in records if r["lead_score"] == "high")
            logger.info("  → %d registros merged · %d leads HIGH", len(records), high)
        time.sleep(0.5)

    if not all_records:
        raise RuntimeError("Ningún registro fue enriquecido correctamente.")

    df = build_dataframe(all_records)
    high_total = len(df[df["lead_score"] == "high"])
    logger.info("Resumen: %d total · %d HIGH · %d MEDIUM · %d descartados",
                len(df),
                high_total,
                len(df[df["lead_score"] == "medium"]),
                len(df[df["lead_score"] == "discard"]))
    return save_csv(df)


if __name__ == "__main__":
    output = run_lead_enricher()
    logger.info("Pipeline leads completo → %s", output)
