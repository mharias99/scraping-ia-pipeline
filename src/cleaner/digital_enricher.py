"""
Digital Enricher V2 — Auditoría de Presencia Digital

Pipeline en dos mitades:
  Mitad A — Maps (0-50, Python puro, sin IA):
    Rating < 3.0       → +25  |  Rating 3.0-3.5  → +15  |  Rating 3.5-4.0 → +5
    < 10 reseñas       → +10  |  Sin reseñas      → +10
    Reseñas recientes negativas detectadas → +10
    Perfil no reclamado → +5

  Mitad B — Web (0-50, Firecrawl):
    Sin web (fijo)     → +25
    Web caída / HTTP   → +20
    Sin reserva online → +20
    Sin píxel Meta/GA  → +10

  Gate de auto-descarte: rating ≥ 4.5 AND reseñas ≥ 100 → DISCARD (no gasta Firecrawl)
  Bandas: HIGH ≥ 60 · MEDIUM 40-59 · LOW < 40

Claude Haiku recibe el JSON fusionado Maps + Web y genera:
  - weaknesses: lista concreta de puntos de dolor
  - call_script: apertura de llamada personalizada con datos reales de ambas mitades
"""

import logging
import os
import time
from datetime import date
from pathlib import Path
from typing import Any

import anthropic
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path("data/output")

# ── Scoring V2 ────────────────────────────────────────────────────────────────

def maps_score_v2(biz: dict[str, Any]) -> int:
    """Calcula el dolor Maps (0–50) sin llamadas a IA."""
    score = 0
    rating  = biz.get("rating")
    reviews = biz.get("review_count") or 0

    if rating is None:
        score += 15
    elif rating < 3.0:
        score += 25
    elif rating < 3.5:
        score += 15
    elif rating < 4.0:
        score += 5

    if reviews == 0:
        score += 10
    elif reviews < 10:
        score += 10

    if not biz.get("claimed"):
        score += 5

    return min(score, 50)


def is_healthy(biz: dict[str, Any]) -> bool:
    """Gate de auto-descarte: negocio con buena reputación → no gastar Firecrawl."""
    rating  = biz.get("rating") or 0.0
    reviews = biz.get("review_count") or 0
    return float(rating) >= 4.5 and int(reviews) >= 100


def total_score(biz: dict[str, Any]) -> int:
    return min((biz.get("maps_score", 0) or 0) + (biz.get("web_score", 0) or 0), 100)


def band_from_score(score: int) -> str:
    if score >= 45:
        return "HIGH"
    if score >= 25:
        return "MEDIUM"
    return "LOW"


# ── Deduplicación ─────────────────────────────────────────────────────────────

def dedup_businesses(businesses: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Elimina duplicados por teléfono o dominio web."""
    from urllib.parse import urlparse

    seen_phones:  set[str] = set()
    seen_domains: set[str] = set()
    unique = []

    for biz in businesses:
        phone  = (biz.get("phone") or "").strip().replace(" ", "")
        web    = (biz.get("website") or "").strip()
        domain = ""
        if web:
            try:
                domain = urlparse(web if web.startswith("http") else f"https://{web}").netloc.lower().lstrip("www.")
            except Exception:
                pass

        if phone and phone in seen_phones:
            continue
        if domain and domain in seen_domains:
            continue

        if phone:
            seen_phones.add(phone)
        if domain:
            seen_domains.add(domain)
        unique.append(biz)

    removed = len(businesses) - len(unique)
    if removed:
        logger.info("[digital] Deduplicados: %d eliminados (%d únicos)", removed, len(unique))
    return unique


# ── Claude tool ───────────────────────────────────────────────────────────────

DIGITAL_AUDIT_TOOL_V2 = {
    "name": "audit_digital_v2",
    "description": (
        "Analyzes a local business's combined Maps + Web digital presence "
        "and generates a personalized cold call opening for a marketing agency. "
        "You receive pre-calculated scores — use them to craft specific, data-driven weaknesses."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "businesses": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "index": {"type": "integer"},
                        "weaknesses": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": (
                                "2-4 concrete, specific weaknesses using the actual data provided. "
                                "Examples: 'Rating 3.1 con 8 reseñas negativas sin responder', "
                                "'Web sin HTTPS — navegadores muestran alerta de inseguridad', "
                                "'Sin formulario de reserva online — los pacientes llaman o se van'. "
                                "Never generic. Always quote numbers or facts from the input."
                            ),
                        },
                        "call_script": {
                            "type": "string",
                            "description": (
                                "2-3 sentence cold call opening in Spanish. "
                                "MUST reference at least one Maps fact AND one web fact (if available). "
                                "Open with the most expensive pain point first. "
                                "End with a concrete proposal or question. "
                                "Tone: confident, direct, no fluff. "
                                "Example: 'Hola, llamo porque veo que tenéis 8 reseñas negativas sin responder "
                                "en Google esta semana, pero lo más caro es que en vuestra web los pacientes "
                                "no pueden reservar cita y se van a la competencia que sí puede. "
                                "Nosotros os lo resolvemos todo este mes, ¿tiene 5 minutos?'"
                            ),
                        },
                    },
                    "required": ["index", "weaknesses", "call_script"],
                },
            }
        },
        "required": ["businesses"],
    },
}


def _build_prompt_v2(batch: list[dict[str, Any]]) -> str:
    lines = ["Analyze each business's Maps + Web digital presence. Use ALL provided data.\n"]
    for i, biz in enumerate(batch):
        lines.append(f"--- NEGOCIO [{i}] ---")
        lines.append(f"Nombre: {biz.get('name', '')}")
        lines.append(f"Categoría: {biz.get('category', '')}")
        lines.append(f"Teléfono: {biz.get('phone', 'No disponible')}")
        # Maps data
        lines.append(f"[MAPS] Rating: {biz.get('rating', 'Sin datos')} "
                     f"({biz.get('review_count', 0)} reseñas) | "
                     f"Perfil reclamado: {'Sí' if biz.get('claimed') else 'NO'}")
        lines.append(f"[MAPS] Score dolor: {biz.get('maps_score', 0)}/50")
        # Web data
        web_status = biz.get("web_status", "no_web")
        if web_status == "no_web":
            lines.append("[WEB] Sin web registrada")
        elif web_status == "revisar_manual":
            lines.append(f"[WEB] Web: {biz.get('website','')} — no responde/timeout")
        elif web_status == "down":
            lines.append(f"[WEB] Web CAÍDA: {biz.get('website','')}")
        else:
            lines.append(f"[WEB] Web: {biz.get('website','')} | "
                         f"HTTPS: {'Sí' if biz.get('web_https') else 'NO'} | "
                         f"Reserva online: {'Sí' if biz.get('web_booking') else 'NO'} | "
                         f"Píxel Meta: {'Sí' if biz.get('web_pixel_meta') else 'NO'} | "
                         f"Google Analytics: {'Sí' if biz.get('web_pixel_ga') else 'NO'}")
        lines.append(f"[WEB] Score dolor: {biz.get('web_score', 0)}/50")
        lines.append(f"SCORE TOTAL: {biz.get('digital_score', 0)}/100 → banda {biz.get('priority','?')}")
        lines.append("")
    return "\n".join(lines)


def _enrich_batch_v2(
    client: anthropic.Anthropic,
    batch: list[dict[str, Any]],
    model: str,
    attempt: int = 1,
) -> list[dict[str, Any]]:
    from cleaner._claude_retry import call_with_retry

    def _call() -> list[dict[str, Any]]:
        response = client.messages.create(
            model=model,
            max_tokens=2048,
            tools=[DIGITAL_AUDIT_TOOL_V2],
            tool_choice={"type": "tool", "name": "audit_digital_v2"},
            messages=[{"role": "user", "content": _build_prompt_v2(batch)}],
        )
        tool_block = next((b for b in response.content if b.type == "tool_use"), None)
        if not tool_block:
            raise ValueError("No tool_use block in response.")
        return tool_block.input.get("businesses", [])

    return call_with_retry(_call, context=f"digital batch ({len(batch)} negocios)", attempt=attempt)


# ── Orquestador V2 ────────────────────────────────────────────────────────────

def enrich_businesses(
    businesses: list[dict[str, Any]],
    model: str = "claude-haiku-4-5-20251001",
    batch_size: int = 5,
    top_n_firecrawl: int = 25,
) -> list[dict[str, Any]]:
    """
    Orquesta el pipeline V2 completo:
      1. Deduplicar por teléfono/dominio
      2. Calcular maps_score (0-50) + aplicar gate de auto-descarte
      3. Inspeccionar webs con Firecrawl (solo top_n_firecrawl que pasan el gate)
      4. Calcular score total (0-100) + banda
      5. Claude genera weaknesses + call_script con JSON fusionado
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY no definida en .env")
    client = anthropic.Anthropic(api_key=api_key)

    # Paso 0: Eliminar negocios cerrados permanentemente (no son leads)
    before = len(businesses)
    businesses = [b for b in businesses if not b.get("permanently_closed")]
    closed = before - len(businesses)
    if closed:
        logger.info("[digital] %d negocios cerrados permanentemente eliminados", closed)

    # Paso 1: Deduplicar
    businesses = dedup_businesses(businesses)

    # Paso 2: Maps pre-score + gate
    discarded = 0
    candidates = []
    for biz in businesses:
        if is_healthy(biz):
            biz["discarded"] = True
            discarded += 1
        else:
            biz["maps_score"] = maps_score_v2(biz)
            biz["discarded"]  = False
            candidates.append(biz)

    logger.info("[digital] %d total | %d descartados (sanos) | %d candidatos",
                len(businesses), discarded, len(candidates))

    if not candidates:
        logger.warning("[digital] Todos los negocios son sanos — sin candidatos")
        return []

    # Paso 3: Inspección web con Firecrawl (solo top_n_firecrawl)
    from scraper.web_inspector import inspect_websites
    candidates = inspect_websites(candidates, top_n=top_n_firecrawl)

    # Paso 4: Score total + banda
    for biz in candidates:
        score = total_score(biz)
        biz["digital_score"] = score
        biz["priority"]      = band_from_score(score)

    # Paso 5: Claude — solo HIGH y MEDIUM (no gastar tokens en LOW)
    to_enrich = [b for b in candidates if b.get("priority") in ("HIGH", "MEDIUM")]
    logger.info("[digital] %d candidatos → %d HIGH+MEDIUM para Claude",
                len(candidates), len(to_enrich))

    batches = [to_enrich[i: i + batch_size] for i in range(0, len(to_enrich), batch_size)]
    for n, batch in enumerate(batches, 1):
        logger.info("[digital] Claude batch %d/%d...", n, len(batches))
        results = _enrich_batch_v2(client, batch, model)
        result_map = {r["index"]: r for r in results}
        for i, biz in enumerate(batch):
            meta = result_map.get(i, {})
            biz["weaknesses"]  = "; ".join(meta.get("weaknesses") or [])
            biz["call_script"] = meta.get("call_script", "")
        time.sleep(0.5)

    # LOW: sin script de Claude
    for biz in candidates:
        if biz.get("priority") == "LOW":
            biz.setdefault("weaknesses",  "")
            biz.setdefault("call_script", "")

    high   = sum(1 for b in candidates if b.get("priority") == "HIGH")
    medium = sum(1 for b in candidates if b.get("priority") == "MEDIUM")
    logger.info("[digital] Resultado: %d HIGH | %d MEDIUM | %d LOW",
                high, medium, len(candidates) - high - medium)
    return candidates


# ── DataFrame + CSV ───────────────────────────────────────────────────────────

def build_digital_dataframe(records: list[dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(records)
    if df.empty:
        return df
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    df["_sort"] = df.get("priority", pd.Series(dtype=str)).map(order).fillna(3)
    df = df.sort_values(["_sort", "digital_score"], ascending=[True, False])
    df = df.drop(columns=["_sort", "discarded"], errors="ignore").reset_index(drop=True)
    return df


def save_digital_csv(df: pd.DataFrame, client_id: str) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / f"digital_{client_id}_{date.today().strftime('%Y%m%d')}.csv"
    export_cols = [
        "priority", "name", "category", "digital_score", "maps_score", "web_score",
        "rating", "review_count", "has_website", "website", "web_https",
        "web_booking", "web_pixel_meta", "web_pixel_ga", "web_status",
        "phone", "address", "weaknesses", "call_script",
        "maps_url", "search_query", "scraped_at",
    ]
    cols = [c for c in export_cols if c in df.columns]
    df[cols].to_csv(path, index=False, encoding="utf-8")
    logger.info("[digital] CSV exportado: %s (%d negocios)", path, len(df))
    return path
