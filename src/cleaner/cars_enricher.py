"""
Cars Enricher — Pipeline de Arbitraje de Vehículos

Lógica pura en pandas, sin llamadas a IA:
  1. Extrae año y km del título/descripción con regex
  2. Agrupa por (modelo_normalizado, año_bucket, km_bucket)
  3. Calcula mediana de precio por grupo
  4. Marca como HIGH los coches que están N% por debajo de la mediana
"""

import logging
import re
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path("data/output")

# ── Regex ─────────────────────────────────────────────────────────────────────

_YEAR_RE = re.compile(r'\b(19[89]\d|20[012]\d)\b')
_KM_RE   = re.compile(r'(\d{1,3}(?:[.\s]\d{3})*)\s*(?:km|kms|kilómetros|k\.?m\.?)', re.IGNORECASE)
_BRAND_RE = re.compile(
    r'\b(seat|volkswagen|vw|renault|ford|opel|peugeot|citroen|toyota|honda|'
    r'hyundai|kia|skoda|dacia|nissan|mazda|bmw|mercedes|audi|volvo|cupra|fiat)\b',
    re.IGNORECASE,
)


def _parse_year(text: str) -> int | None:
    m = _YEAR_RE.search(text)
    return int(m.group(1)) if m else None


def _parse_km(text: str) -> int | None:
    m = _KM_RE.search(text)
    if not m:
        return None
    raw = re.sub(r'[\s.]', '', m.group(1))
    try:
        return int(raw)
    except ValueError:
        return None


def _year_bucket(year: int | None) -> str:
    if year is None:
        return "desconocido"
    if year >= 2020:
        return "2020+"
    if year >= 2015:
        return "2015-2019"
    if year >= 2010:
        return "2010-2014"
    return "<2010"


def _km_bucket(km: int | None) -> str:
    if km is None:
        return "desconocido"
    if km < 50_000:
        return "0-50k"
    if km < 100_000:
        return "50k-100k"
    if km < 150_000:
        return "100k-150k"
    return "150k+"


def _normalize_model(model_query: str) -> str:
    """Limpia la query del modelo para usarla como clave de agrupación."""
    return model_query.lower().strip()


# ── Enriquecimiento ───────────────────────────────────────────────────────────

def enrich_cars(
    listings: list[dict[str, Any]],
    arbitrage_threshold: float = 0.15,
) -> list[dict[str, Any]]:
    """
    Añade year, km, market_median, price_delta_pct y opportunity a cada listing.
    Filtra anuncios sin precio.
    """
    enriched = []
    for lst in listings:
        combined = f"{lst.get('title', '')} {lst.get('description', '')}"
        # Preferir valores ya extraídos por el scraper; parsear del texto solo si faltan
        year = lst.get("year") or _parse_year(combined)
        km   = lst.get("km")   or _parse_km(combined)
        lst["year"]       = year
        lst["km"]         = km
        lst["year_bucket"] = _year_bucket(year)
        lst["km_bucket"]   = _km_bucket(km)
        lst["model_key"]   = _normalize_model(lst.get("model_query", ""))
        enriched.append(lst)

    df = pd.DataFrame(enriched)
    if df.empty:
        return []

    # Solo trabajamos con listings que tienen precio numérico
    df = df[df["price"].notna() & (df["price"] > 0)].copy()
    if df.empty:
        logger.warning("[cars_enricher] Ningún listing tiene precio numérico")
        return []

    # Limpiar columnas que el enricher recalculará (evita conflictos en el merge)
    df.drop(columns=["market_median", "price_delta_pct", "opportunity"], errors="ignore", inplace=True)

    # Calcular mediana de mercado por grupo
    # Solo grupos con ≥ MIN_SAMPLE_SIZE anuncios tienen mediana fiable;
    # los grupos pequeños se marcan UNKNOWN para evitar falsos positivos HIGH.
    MIN_SAMPLE_SIZE = 5
    group_cols = ["model_key", "year_bucket", "km_bucket"]

    group_sizes = (
        df.groupby(group_cols)["price"]
        .count()
        .reset_index()
        .rename(columns={"price": "_n"})
    )
    medians = (
        df.groupby(group_cols)["price"]
        .median()
        .reset_index()
        .rename(columns={"price": "market_median"})
    )
    medians = medians.merge(group_sizes, on=group_cols, how="left")
    small_groups = (medians["_n"] < MIN_SAMPLE_SIZE).sum()
    if small_groups:
        logger.warning(
            "[cars_enricher] %d grupos con n<%d — market_median anulada (→ UNKNOWN)",
            small_groups, MIN_SAMPLE_SIZE,
        )
    medians.loc[medians["_n"] < MIN_SAMPLE_SIZE, "market_median"] = None
    medians.drop(columns=["_n"], inplace=True)

    df = df.merge(medians, on=group_cols, how="left")

    # Delta de precio respecto a la mediana
    df["price_delta_pct"] = (df["market_median"] - df["price"]) / df["market_median"]

    # Clasificar oportunidad
    def _classify(row: pd.Series) -> str:
        if pd.isna(row["market_median"]) or pd.isna(row["price_delta_pct"]):
            return "UNKNOWN"
        delta = row["price_delta_pct"]
        if delta >= arbitrage_threshold:
            return "HIGH"
        if delta >= arbitrage_threshold / 2:
            return "MEDIUM"
        if delta >= 0:
            return "NORMAL"
        return "SOBREVALORADO"

    df["opportunity"] = df.apply(_classify, axis=1)

    # Limpiar columnas internas de agrupación
    df.drop(columns=["model_key", "year_bucket", "km_bucket"], errors="ignore", inplace=True)

    high = len(df[df["opportunity"] == "HIGH"])
    logger.info("[cars_enricher] %d listings · %d HIGH · %d MEDIUM",
                len(df), high, len(df[df["opportunity"] == "MEDIUM"]))

    return df.to_dict(orient="records")


def build_cars_dataframe(records: list[dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(records)
    if df.empty:
        return df

    # Ordenar: HIGH primero, luego MEDIUM, luego NORMAL
    order = {"HIGH": 0, "MEDIUM": 1, "NORMAL": 2, "SOBREVALORADO": 3, "UNKNOWN": 4}
    df["_sort"] = df["opportunity"].map(order).fillna(4)
    df = df.sort_values("_sort").drop(columns=["_sort"]).reset_index(drop=True)

    # Redondear columnas numéricas
    for col in ["price", "market_median"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").round(0)
    if "price_delta_pct" in df.columns:
        df["price_delta_pct"] = (df["price_delta_pct"] * 100).round(1).astype(str) + "%"

    return df


def save_cars_csv(df: pd.DataFrame, client_id: str) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / f"cars_{client_id}_{date.today().strftime('%Y%m%d')}.csv"

    export_cols = [
        "opportunity", "title", "price", "market_median", "price_delta_pct",
        "year", "km", "location", "phone", "url", "model_query", "scraped_at",
    ]
    cols = [c for c in export_cols if c in df.columns]
    df[cols].to_csv(path, index=False, encoding="utf-8")
    logger.info("[cars_enricher] CSV exportado: %s (%d rows)", path, len(df))
    return path
