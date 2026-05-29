import argparse
import asyncio
import json
import logging
import logging.handlers
import os
import time
from datetime import date
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()

# ── Logging: consola + fichero rotativo diario ────────────────────────────────
Path("logs").mkdir(exist_ok=True)
_fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
_file_handler = logging.handlers.TimedRotatingFileHandler(
    "logs/pipeline.log", when="midnight", backupCount=30, encoding="utf-8"
)
_file_handler.setFormatter(_fmt)
_console_handler = logging.StreamHandler()
_console_handler.setFormatter(_fmt)

logging.basicConfig(level=logging.INFO, handlers=[_console_handler, _file_handler])
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Pipeline B2B: Scraping + IA + Sheets",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python src/main.py --config configs/cliente_ejemplo.yaml
  python src/main.py --config configs/cliente_ejemplo.yaml --skip-scrape
  python src/main.py --config configs/cliente_ejemplo.yaml --skip-sheets
        """,
    )
    parser.add_argument("--config", type=str, help="Ruta al archivo YAML del cliente")
    parser.add_argument("--skip-scrape",  action="store_true", help="Usar datos raw existentes")
    parser.add_argument("--skip-enrich",  action="store_true", help="Solo scraping, sin IA")
    parser.add_argument("--skip-sheets",  action="store_true", help="No exportar a Google Sheets")
    return parser.parse_args()


def step_scrape(cfg: Any) -> Path:
    from scraper.indeed_scraper import run_indeed_scraper, save_raw

    logger.info("── PASO 1/3: Scraping Indeed (%d queries, max %d resultados) ──",
                len(cfg.scraper.queries), cfg.scraper.max_results)

    jobs = asyncio.run(run_indeed_scraper(
        max_pages_per_query=cfg.scraper.max_pages_per_query,
        max_detail_pages=cfg.scraper.max_results,
    ))
    if not jobs:
        raise RuntimeError("El scraper no devolvió datos. Abortando.")

    raw_path = Path(f"data/raw/{cfg.client_id}_raw.json")
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(jobs, f, ensure_ascii=False, indent=2)

    logger.info("Paso 1 completo — %d ofertas → %s", len(jobs), raw_path)
    return raw_path


def step_enrich(cfg: Any, raw_path: Path) -> Path:
    import anthropic
    import pandas as pd
    from cleaner.lead_enricher import (
        enrich_batch, merge_results, build_dataframe, sanitize_email_lopd
    )

    logger.info("── PASO 2/3: Enriquecimiento con Claude (%s, batch=%d) ──",
                cfg.enricher.model, cfg.enricher.batch_size)

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY no definida en .env")

    with open(raw_path, encoding="utf-8") as f:
        raw_data: list[dict[str, Any]] = json.load(f)

    client = anthropic.Anthropic(api_key=api_key)
    all_records: list[dict[str, Any]] = []
    batches = [raw_data[i: i + cfg.enricher.batch_size]
               for i in range(0, len(raw_data), cfg.enricher.batch_size)]

    for n, batch in enumerate(batches, 1):
        logger.info("  Batch %d/%d...", n, len(batches))
        enriched = enrich_batch(client, batch)
        if enriched:
            records = merge_results(batch, enriched)
            all_records.extend(records)
        time.sleep(0.5)

    if not all_records:
        raise RuntimeError("Ningún registro enriquecido correctamente.")

    # Filtrar por min_score
    score_order = {"high": 0, "medium": 1, "low": 2, "discard": 3, "all": 99}
    min_val = score_order.get(cfg.enricher.min_score, 2)
    filtered = [r for r in all_records
                if score_order.get(r.get("lead_score", "discard"), 3) <= min_val]

    df = build_dataframe(filtered)
    output_dir = Path("data/output")
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / f"leads_{cfg.client_id}_{date.today().strftime('%Y%m%d')}.csv"
    df.to_csv(csv_path, index=False, encoding="utf-8")

    high = len(df[df["lead_score"] == "high"])
    med  = len(df[df["lead_score"] == "medium"])
    logger.info("Paso 2 completo — %d leads (%d HIGH, %d MEDIUM) → %s",
                len(df), high, med, csv_path)
    return csv_path


def step_sheets(cfg: Any, csv_path: Path) -> str:
    import pandas as pd
    from delivery.sheets_exporter import (
        get_client, prepare_dataframe, export_to_sheets
    )

    sheets_cfg = cfg.delivery.google_sheets
    if not sheets_cfg.enabled:
        logger.info("── PASO 3/3: Google Sheets desactivado en config ──")
        return ""

    logger.info("── PASO 3/3: Exportando a Google Sheets ──")

    spreadsheet_id = sheets_cfg.spreadsheet_id or os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID", "")
    if not spreadsheet_id:
        raise EnvironmentError(
            "spreadsheet_id no definido. Añádelo en el YAML o en GOOGLE_SHEETS_SPREADSHEET_ID."
        )

    df = prepare_dataframe(__import__("pandas").read_csv(csv_path))
    gc = get_client()

    # Nombre de la hoja = config + nombre del cliente
    worksheet = f"{sheets_cfg.worksheet_name} · {cfg.client_name}"
    url = export_to_sheets(df, spreadsheet_id, worksheet, gc)

    logger.info("Paso 3 completo — Sheet actualizado: %s", url)
    return url


def run_pipeline(args: argparse.Namespace) -> None:
    start = time.perf_counter()

    # ── Cargar config ─────────────────────────────────────────────────────────
    if args.config:
        from config import load_config
        cfg = load_config(args.config)
        logger.info("Config cargada: cliente='%s' (%s)", cfg.client_name, args.config)
    else:
        # Sin config: comportamiento legacy con valores por defecto
        from config import PipelineConfig
        cfg = PipelineConfig()
        logger.info("Sin config — usando valores por defecto")

    raw_path = Path(f"data/raw/{cfg.client_id}_raw.json")

    # ── Paso 1: Scraping ──────────────────────────────────────────────────────
    if args.skip_scrape:
        if not raw_path.exists():
            raise FileNotFoundError(f"--skip-scrape activo pero no existe {raw_path}")
        logger.info("── PASO 1/3 omitido — usando %s ──", raw_path)
    else:
        raw_path = step_scrape(cfg)

    if args.skip_enrich:
        logger.info("── PASOS 2/3 y 3/3 omitidos ──")
        logger.info("Pipeline completo en %.1fs", time.perf_counter() - start)
        return

    # ── Paso 2: Enriquecimiento ───────────────────────────────────────────────
    csv_path = step_enrich(cfg, raw_path)

    # ── Paso 3: Entrega ───────────────────────────────────────────────────────
    if not args.skip_sheets:
        step_sheets(cfg, csv_path)

    # CRM export siempre (no requiere credenciales externas)
    from delivery.crm_exporter import run_crm_export
    crm_paths = run_crm_export(min_score=cfg.enricher.min_score)

    elapsed = time.perf_counter() - start
    logger.info("═══ PIPELINE COMPLETO en %.1fs ═══", elapsed)
    logger.info("CSV       → %s", csv_path)
    logger.info("HubSpot   → %s", crm_paths["hubspot"])
    logger.info("Pipedrive → %s", crm_paths["pipedrive"])


if __name__ == "__main__":
    run_pipeline(parse_args())
