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


def _dedup(jobs: list[Any]) -> list[Any]:
    """Deduplica por URL cuando existe; si no, por (empresa|título) normalizado.
    Esto elimina duplicados cross-source (misma oferta en InfoJobs e Indeed).
    """
    seen: set[str] = set()
    result = []
    for j in jobs:
        url = (j.get("url") or "").strip().rstrip("/").lower()
        if url:
            key = url
        else:
            company = (j.get("company") or "").strip().lower()
            title   = (j.get("title")   or "").strip().lower()
            key = f"{company}|{title}"
        if key and key not in seen:
            seen.add(key)
            result.append(j)
    return result


def _run_firecrawl(cfg: Any, max_res: int) -> list[Any]:
    from scraper.firecrawl_scraper import run_firecrawl_scraper
    queries     = cfg.scraper.queries
    ij_queries  = cfg.scraper.infojobs_queries or queries
    ind_queries = cfg.scraper.indeed_queries   or queries
    max_pages   = cfg.scraper.max_pages_per_query
    half        = max_res // 2
    jobs_ij  = run_firecrawl_scraper(queries=ij_queries,  sources=["infojobs"],
                                     max_results=half,            max_pages_per_query=max_pages)
    jobs_ind = run_firecrawl_scraper(queries=ind_queries, sources=["indeed"],
                                     max_results=max_res - half,  max_pages_per_query=max_pages)
    return jobs_ij + jobs_ind


def _run_apify(cfg: Any, max_res: int) -> list[Any]:
    from scraper.apify_scraper import run_apify_scraper
    apify_cfg  = cfg.scraper.apify
    base_q     = cfg.scraper.queries
    ij_queries = apify_cfg.infojobs_queries or cfg.scraper.infojobs_queries or base_q
    ind_queries = apify_cfg.indeed_queries  or cfg.scraper.indeed_queries   or base_q
    # Mezcla de queries: InfoJobs con sus queries, Indeed con las suyas
    queries_by_source = {"infojobs": ij_queries, "indeed": ind_queries}
    # Llamada unificada con queries intercaladas por fuente
    all_jobs: list[Any] = []
    for source, q_list in queries_by_source.items():
        jobs = run_apify_scraper(
            queries=q_list,
            sources=[source],
            actors={source: apify_cfg.actor_infojobs if source == "infojobs" else apify_cfg.actor_indeed},
            max_results=max_res,
            max_items_per_query=apify_cfg.max_items_per_query,
            location=cfg.scraper.location,
        )
        all_jobs.extend(jobs)
    return all_jobs


def step_scrape(cfg: Any) -> Path:
    source  = cfg.scraper.source.lower()
    queries = cfg.scraper.queries
    max_res = cfg.scraper.max_results
    raw_path = Path(f"data/raw/{cfg.client_id}_raw.json")
    raw_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("── PASO 1/3: Scraping [%s] (%d queries, max %d) ──",
                source, len(queries), max_res)

    # ── Fuentes activas ───────────────────────────────────────────────────────
    if source == "job_adapter":
        # B2B empleo vía JobSourceAdapter (mock / validation / production)
        # Configura JOB_SOURCE_MODE en .env; ver src/scraper/job_source_adapter.py
        from scraper.job_source_adapter import create_adapter
        adapter   = create_adapter()
        ij_q      = cfg.scraper.infojobs_queries or queries
        ind_q     = cfg.scraper.indeed_queries   or queries
        all_q     = list(dict.fromkeys(ij_q + ind_q))   # dedup preservando orden
        jobs_raw  = adapter.fetch_jobs(all_q, cfg.scraper.location, max_res // max(len(all_q), 1))
        jobs = _dedup(jobs_raw)[:max_res]

    elif source == "gmaps":
        from scraper.gmaps_scraper import run_gmaps_scraper
        gs = cfg.gmaps_scraper
        jobs = run_gmaps_scraper(
            search_queries=gs.search_queries,
            location=gs.location,
            max_results_per_query=gs.max_results_per_query,
            language=gs.language,
        )

    # ── Fuentes deprecated (código en _deprecated/) ───────────────────────────
    # Estas rutas siguen funcionando mientras haya configs que las usen,
    # pero no se recomienda para nuevos clientes.

    elif source in ("firecrawl", "apify", "both"):
        logger.warning(
            "⚠️  source='%s' usa scrapers deprecados (ToS riesgo). "
            "Migra a source='job_adapter' con JOB_SOURCE_MODE en .env.",
            source,
        )
        if source == "firecrawl":
            jobs = _dedup(_run_firecrawl(cfg, max_res))[:max_res]
        elif source == "apify":
            jobs = _dedup(_run_apify(cfg, max_res))[:max_res]
        else:
            fc_target    = max_res // 2
            apify_target = max_res - fc_target
            jobs = _dedup(_run_firecrawl(cfg, fc_target) + _run_apify(cfg, apify_target))[:max_res]

    elif source == "indeed":
        logger.warning("⚠️  source='indeed' usa scraper Playwright deprecado.")
        from scraper.indeed_scraper import run_indeed_scraper
        jobs = asyncio.run(run_indeed_scraper(
            max_pages_per_query=cfg.scraper.max_pages_per_query,
            max_detail_pages=max_res,
        ))

    elif source == "milanuncios":
        raise ValueError(
            "source='milanuncios' (vertical Coches) está CONGELADA. "
            "Ver _frozen_coches/README.md para condiciones de reactivación."
        )

    else:
        raise ValueError(
            f"Fuente desconocida: '{source}'.\n"
            "  B2B empleo:        source: job_adapter  (+ JOB_SOURCE_MODE en .env)\n"
            "  Auditoría digital: source: gmaps\n"
            "  Coches:            CONGELADA — ver _frozen_coches/README.md"
        )

    if not jobs:
        raise RuntimeError("El scraper no devolvió datos. Abortando.")

    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(jobs, f, ensure_ascii=False, indent=2)

    logger.info("Paso 1 completo — %d ofertas → %s", len(jobs), raw_path)
    return raw_path


def step_enrich(cfg: Any, raw_path: Path) -> Path:
    pipeline_type = getattr(cfg, "pipeline_type", "b2b_leads")

    if pipeline_type == "car_arbitrage":
        return _enrich_cars(cfg, raw_path)
    if pipeline_type == "digital_audit":
        return _enrich_digital(cfg, raw_path)
    return _enrich_b2b(cfg, raw_path)


def _enrich_b2b(cfg: Any, raw_path: Path) -> Path:
    import anthropic
    from cleaner.lead_enricher import enrich_batch, merge_results, build_dataframe

    logger.info("── PASO 2/3: B2B Lead Enrichment (%s, batch=%d) ──",
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


def _enrich_cars(cfg: Any, raw_path: Path) -> Path:
    from cleaner.cars_enricher import enrich_cars, build_cars_dataframe, save_cars_csv

    logger.info("── PASO 2/3: Car Arbitrage Analysis ──")

    with open(raw_path, encoding="utf-8") as f:
        raw_data: list[dict[str, Any]] = json.load(f)

    enriched = enrich_cars(raw_data, arbitrage_threshold=cfg.car_scraper.arbitrage_threshold)
    if not enriched:
        raise RuntimeError("Sin listings con precio para analizar.")

    df = build_cars_dataframe(enriched)
    csv_path = save_cars_csv(df, cfg.client_id)

    high = len(df[df["opportunity"] == "HIGH"])
    logger.info("Paso 2 completo — %d listings · %d HIGH → %s", len(df), high, csv_path)
    return csv_path


def _enrich_digital(cfg: Any, raw_path: Path) -> Path:
    from cleaner.digital_enricher import enrich_businesses, build_digital_dataframe, save_digital_csv

    logger.info("── PASO 2/3: Digital Audit V2 (%s, batch=%d, top_n_firecrawl=%d) ──",
                cfg.enricher.model, cfg.enricher.batch_size,
                cfg.gmaps_scraper.max_results_per_query)

    with open(raw_path, encoding="utf-8") as f:
        raw_data: list[dict[str, Any]] = json.load(f)

    enriched = enrich_businesses(
        raw_data,
        model=cfg.enricher.model,
        batch_size=cfg.enricher.batch_size,
        top_n_firecrawl=cfg.gmaps_scraper.max_results_per_query,
    )
    if not enriched:
        raise RuntimeError("Sin negocios para auditar.")

    df = build_digital_dataframe(enriched)
    csv_path = save_digital_csv(df, cfg.client_id)

    high = len(df[df["priority"] == "HIGH"])
    logger.info("Paso 2 completo — %d negocios · %d HIGH → %s", len(df), high, csv_path)
    return csv_path


def _export_run_stats(cfg: Any, raw_path: Path, csv_path: Path, elapsed: float) -> None:
    """Calcula métricas de la ejecución y las escribe en data/web/stats.json."""
    import pandas as pd
    from delivery.stats_exporter import export_pipeline_stats

    pipeline_type = getattr(cfg, "pipeline_type", "b2b_leads")

    with open(raw_path, encoding="utf-8") as f:
        raw_data: list[dict[str, Any]] = json.load(f)
    df = pd.read_csv(csv_path)

    if pipeline_type == "b2b_leads":
        score = df["lead_score"] if "lead_score" in df.columns else pd.Series(dtype=str)
        leads_high    = int((score == "high").sum())
        leads_medium  = int((score == "medium").sum())
        leads_low     = int((score == "low").sum())
        indeed_offers  = sum(1 for j in raw_data if "indeed"   in j.get("source", "").lower())
        ij_offers      = sum(1 for j in raw_data if "infojobs" in j.get("source", "").lower())
        stats: dict[str, Any] = {
            "offers_extracted": len(raw_data),
            "leads_qualified":  len(df),
            "leads_high":       leads_high,
            "leads_medium":     leads_medium,
            "leads_low":        leads_low,
            "leads_discard":    len(raw_data) - len(df),
            "pipeline_time_s":  round(elapsed, 1),
            "sources": {
                "indeed":   {"offers": indeed_offers or max(len(raw_data) - ij_offers, 0)},
                "infojobs": {"offers": ij_offers},
            },
        }

    elif pipeline_type == "car_arbitrage":
        opp = df["opportunity"] if "opportunity" in df.columns else pd.Series(dtype=str)
        avg_delta = 0
        if "price" in df.columns and "market_median" in df.columns:
            high_df = df[opp == "HIGH"]
            if not high_df.empty:
                avg_delta = int((high_df["market_median"] - high_df["price"]).mean())
        stats = {
            "ads_analyzed":         len(df),
            "opportunities_high":   int((opp == "HIGH").sum()),
            "opportunities_medium": int((opp == "MEDIUM").sum()),
            "avg_delta_eur":        avg_delta,
            "pipeline_time_s":      round(elapsed, 1),
        }

    elif pipeline_type == "digital_audit":
        pri = df["priority"] if "priority" in df.columns else pd.Series(dtype=str)
        n   = max(len(df), 1)
        pct_no_web = 0
        if "web_status" in df.columns:
            no_web = int(df["web_status"].isna().sum() + (df["web_status"] == "").sum())
            pct_no_web = round(no_web / n * 100)
        pct_no_booking = 0
        if "web_booking" in df.columns:
            no_bk = int((df["web_booking"] == False).sum() + df["web_booking"].isna().sum())  # noqa: E712
            pct_no_booking = round(no_bk / n * 100)
        stats = {
            "businesses_audited": len(df),
            "clients_high":       int((pri == "HIGH").sum()),
            "clients_medium":     int((pri == "MEDIUM").sum()),
            "pct_no_web":         pct_no_web,
            "pct_no_booking":     pct_no_booking,
            "pipeline_time_s":    round(elapsed, 1),
        }
    else:
        return

    export_pipeline_stats(pipeline_type, stats)


def step_sheets(cfg: Any, csv_path: Path) -> str:
    from delivery.sheets_exporter import get_client, prepare_dataframe, append_new_leads
    from delivery.seen_tracker import filter_new, commit

    sheets_cfg    = cfg.delivery.google_sheets
    pipeline_type = getattr(cfg, "pipeline_type", "b2b_leads")

    if not sheets_cfg.enabled:
        logger.info("── PASO 3/3: Google Sheets desactivado en config ──")
        return ""

    logger.info("── PASO 3/3: Exportando a Google Sheets [%s] ──", pipeline_type)

    spreadsheet_id = sheets_cfg.spreadsheet_id or os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID", "")
    if not spreadsheet_id:
        raise EnvironmentError(
            "spreadsheet_id no definido. Añádelo en el YAML o en GOOGLE_SHEETS_SPREADSHEET_ID."
        )

    import pandas as pd
    df_all = prepare_dataframe(pd.read_csv(csv_path), pipeline_type=pipeline_type)

    # Filtrar solo leads nuevos (no vistos en ejecuciones anteriores)
    records = df_all.to_dict(orient="records")
    new_records, updated_seen = filter_new(records, cfg.client_id, pipeline_type)

    if not new_records:
        logger.info("── PASO 3/3: Sin leads nuevos hoy — Sheet sin cambios ──")
        return f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"

    df_new    = pd.DataFrame(new_records)
    gc        = get_client()
    worksheet = f"{sheets_cfg.worksheet_name} · {cfg.client_name}"
    url, n    = append_new_leads(df_new, spreadsheet_id, worksheet, gc, pipeline_type)

    # Persistir seen solo si el export fue exitoso
    commit(cfg.client_id, updated_seen)
    logger.info("── PASO 3/3: %d leads nuevos añadidos al Sheet ──", n)

    # Crear/recrear Dashboard con fórmulas actualizadas
    _dashboard_builders = {
        "b2b_leads":    "build_b2b_dashboard",
        "car_arbitrage": "build_cars_dashboard",
        "digital_audit": "build_digital_dashboard",
    }
    builder_name = _dashboard_builders.get(pipeline_type)
    if builder_name:
        try:
            from delivery import dashboard_builder as _db
            getattr(_db, builder_name)(spreadsheet_id, worksheet, gc)
        except Exception as e:
            logger.warning("Dashboard no creado: %s", str(e)[:80])

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

    # ── Exportar stats para dashboard Next.js (no bloquea el pipeline) ───────
    try:
        _export_run_stats(cfg, raw_path, csv_path, time.perf_counter() - start)
    except Exception as exc:
        logger.warning("[stats] stats.json no exportado: %s", str(exc)[:80])

    # ── Paso 3: Entrega ───────────────────────────────────────────────────────
    if not args.skip_sheets:
        step_sheets(cfg, csv_path)

    # CRM export (solo B2B — Cars/Digital no tienen columnas HubSpot/Pipedrive)
    from delivery.crm_exporter import run_crm_export
    pipeline_type = getattr(cfg, "pipeline_type", "b2b_leads")
    crm_paths = run_crm_export(min_score=cfg.enricher.min_score, pipeline_type=pipeline_type)

    elapsed = time.perf_counter() - start
    logger.info("═══ PIPELINE COMPLETO en %.1fs ═══", elapsed)
    logger.info("CSV       → %s", csv_path)
    logger.info("HubSpot   → %s", crm_paths["hubspot"])
    logger.info("Pipedrive → %s", crm_paths["pipedrive"])


if __name__ == "__main__":
    run_pipeline(parse_args())
