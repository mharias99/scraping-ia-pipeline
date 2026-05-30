"""
JobSourceAdapter — fuente de ofertas de empleo intercambiable.

La interfaz común JobSourceAdapter.fetch_jobs() devuelve siempre el mismo
formato, independientemente del modo. Esto permite cambiar de fuente sin
tocar lead_enricher.py, sheets_exporter.py ni el resto del pipeline.

MODOS (variable de entorno JOB_SOURCE_MODE):
────────────────────────────────────────────────────────────────────────────
  mock         → Datos de ejemplo. Sin credenciales. Para desarrollo y tests.

  validation   → API oficial de InfoJobs (autenticación HTTP Basic).
                 ⚠️  USO ESTRICTAMENTE INTERNO.
                 Los términos de InfoJobs API prohíben el uso comercial de
                 sus datos y la redistribución de contenido. Este modo sirve
                 ÚNICAMENTE para validar que el scoring de "vacante caliente"
                 produce leads que una ETT compraría. NUNCA se contacta a
                 nadie con leads obtenidos en este modo.
                 Los leads se marcan uso="solo_validacion_interna" para que
                 no puedan entrar por error en un flujo de contacto.
                 Credenciales en .env: INFOJOBS_CLIENT_ID, INFOJOBS_CLIENT_SECRET

  production   → Agregador con licencia comercial (TheirStack, LoopCV, etc.).
                 Es el único modo habilitado para generar leads destinados a
                 contacto comercial; la licencia del proveedor ampara ese uso.
                 Credenciales en .env: AGGREGATOR_BASE_URL, AGGREGATOR_API_KEY
────────────────────────────────────────────────────────────────────────────

NUNCA se usa scraping como fallback. Si faltan credenciales del modo elegido,
el sistema falla con mensaje claro indicando qué configurar.

SCORING DE URGENCIA (señales de que la empresa NECESITA cubrir la vacante ya):
  Estas señales son de la EMPRESA (persona jurídica), no de personas físicas.
  Cuanto más alta la urgencia, más caliente es el lead para una ETT.
"""

import base64
import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# ── Pesos del scoring de urgencia (configurables aquí, no valores mágicos) ───
URGENCY_WEIGHTS: dict[str, int] = {
    "days_open":         2,    # puntos por día que lleva abierta
    "repost_count":     15,    # puntos por cada vez que se ha republicado
    "multiple_openings": 20,   # puntos si hay >1 posición abierta del mismo perfil
}
MAX_DAYS_OPEN_SCORE = 60       # cap: 30 días × 2 = 60 pts máximo

# ── ICP: sectores con mayor propensión a usar ETTs ────────────────────────────
ICP_SECTOR_SCORES: dict[str, int] = {
    "logística":        95,
    "manufactura":      90,
    "distribución":     90,
    "almacén":          85,
    "producción":       85,
    "industria":        85,
    "retail":           80,
    "comercio":         80,
    "contabilidad":     80,
    "administración":   75,
    "call center":      75,
    "atención cliente": 70,
    "hostelería":       70,
    "limpieza":         65,
}
ICP_DEFAULT_SCORE = 50   # sectores no listados


def _urgency_score(
    days_open: int | None,
    repost_count: int | None,
    multiple_openings: bool,
) -> int:
    score = 0
    if days_open is not None:
        score += min(days_open * URGENCY_WEIGHTS["days_open"], MAX_DAYS_OPEN_SCORE)
    if repost_count is not None:
        score += repost_count * URGENCY_WEIGHTS["repost_count"]
    if multiple_openings:
        score += URGENCY_WEIGHTS["multiple_openings"]
    return score


def _icp_score(title: str, company_sector: str) -> int:
    """Infiere si la empresa es buen cliente para una ETT basándose en sector/puesto."""
    combined = f"{title} {company_sector}".lower()
    best = ICP_DEFAULT_SCORE
    for sector, pts in ICP_SECTOR_SCORES.items():
        if sector in combined:
            best = max(best, pts)
    return best


def _base_record(
    title: str,
    company: str,
    location: str,
    description: str,
    url: str,
    query: str,
    source_tag: str,
    uso: str,
    posted_days_ago: int | None = None,
    repost_count: int | None = None,
    multiple_openings: bool = False,
    company_sector: str = "",
) -> dict[str, Any]:
    """Construye el dict en el formato que espera lead_enricher.py."""
    u_score = _urgency_score(posted_days_ago, repost_count, multiple_openings)
    i_score = _icp_score(title, company_sector)
    return {
        # Campos existentes (compatibles con lead_enricher)
        "title":        title,
        "company":      company,
        "location":     location,
        "description":  description,
        "url":          url,
        "salary":       "",
        "query":        query,
        "source":       source_tag,
        "scraped_at":   datetime.utcnow().isoformat(),
        # Campos nuevos de scoring y marco legal
        "posted_days_ago":   posted_days_ago,
        "repost_count":      repost_count,
        "urgency_score":     u_score,
        "icp_score":         i_score,
        "fuente_dato":       source_tag,
        "uso":               uso,          # "solo_validacion_interna" | "comercial"
        # Placeholder RGPD para purga por TTL (a rellenar según política del cliente)
        "rgpd_ttl_days":     90,
        "rgpd_opt_out":      "",
    }


# ── Interfaz común ────────────────────────────────────────────────────────────

class JobSourceAdapter(ABC):
    @abstractmethod
    def fetch_jobs(
        self,
        queries: list[str],
        location: str,
        max_per_query: int,
    ) -> list[dict[str, Any]]:
        """Devuelve lista de ofertas en formato interno del pipeline."""


# ── Modo mock ─────────────────────────────────────────────────────────────────

class MockJobAdapter(JobSourceAdapter):
    """
    Devuelve ofertas de ejemplo hardcodeadas.
    Sin credenciales. Para desarrollo y tests.
    """

    _MOCK_JOBS = [
        {
            "title": "Auxiliar Administrativo — Introducción de Datos",
            "company": "Logística Rápida S.L.",
            "location": "Madrid",
            "description": (
                "Buscamos auxiliar para grabación de datos en ERP, control de albaranes "
                "y Excel avanzado. Incorporación inmediata. Contrato inicial 3 meses."
            ),
            "url": "https://mock.example.com/oferta/1",
            "company_sector": "logística",
            "posted_days_ago": 35,
            "repost_count": 2,
            "multiple_openings": True,
        },
        {
            "title": "Operador de Datos — Contabilidad",
            "company": "Distribuidora Centro S.A.",
            "location": "Barcelona",
            "description": (
                "Puesto de grabación de facturas, cuadre de cuentas y gestión de "
                "albaranes en Excel. Buscamos perfil con experiencia en backoffice."
            ),
            "url": "https://mock.example.com/oferta/2",
            "company_sector": "distribución",
            "posted_days_ago": 12,
            "repost_count": 0,
            "multiple_openings": False,
        },
        {
            "title": "Administrativo Facturación",
            "company": "Retail Nacional S.L.",
            "location": "Valencia",
            "description": (
                "Gestión de facturas, control de cobros y pagos. Se requiere "
                "Excel, conocimiento de SAP básico. Jornada completa."
            ),
            "url": "https://mock.example.com/oferta/3",
            "company_sector": "retail",
            "posted_days_ago": 5,
            "repost_count": 1,
            "multiple_openings": False,
        },
        {
            "title": "Data Entry Specialist",
            "company": "Manufactura Levante S.A.",
            "location": "Murcia",
            "description": (
                "Introducción y validación de datos en sistema interno. "
                "Alto volumen de registros diarios. Buscamos 2 perfiles."
            ),
            "url": "https://mock.example.com/oferta/4",
            "company_sector": "manufactura",
            "posted_days_ago": 48,
            "repost_count": 3,
            "multiple_openings": True,
        },
        {
            "title": "Grabador de Datos — Almacén",
            "company": "Centro Logístico Norte",
            "location": "Bilbao",
            "description": (
                "Control de inventario con escáner y ERP. Registro de entradas y "
                "salidas. Turno de mañana. Incorporación esta semana."
            ),
            "url": "https://mock.example.com/oferta/5",
            "company_sector": "almacén",
            "posted_days_ago": 3,
            "repost_count": 0,
            "multiple_openings": False,
        },
    ]

    def fetch_jobs(
        self,
        queries: list[str],
        location: str,
        max_per_query: int,
    ) -> list[dict[str, Any]]:
        logger.info("[job_adapter:mock] Devolviendo %d ofertas de ejemplo", len(self._MOCK_JOBS))
        return [
            _base_record(
                title=j["title"], company=j["company"], location=j["location"],
                description=j["description"], url=j["url"],
                query=queries[0] if queries else "mock",
                source_tag="mock",
                uso="comercial",   # mock puede usarse en demos
                posted_days_ago=j.get("posted_days_ago"),
                repost_count=j.get("repost_count"),
                multiple_openings=j.get("multiple_openings", False),
                company_sector=j.get("company_sector", ""),
            )
            for j in self._MOCK_JOBS[:max_per_query * len(queries)]
        ]


# ── Modo validation — API oficial InfoJobs ────────────────────────────────────

class InfoJobsValidationAdapter(JobSourceAdapter):
    """
    API oficial de InfoJobs — SOLO PARA VALIDACIÓN INTERNA.

    ⚠️  MARCO LEGAL EXPLÍCITO:
    Los Términos de Uso de la API de InfoJobs (https://developer.infojobs.net/
    documentation/terms-of-use.xhtml) permiten el acceso a datos de ofertas
    para uso interno de aplicaciones registradas, pero PROHÍBEN expresamente:
      - La redistribución comercial del contenido de InfoJobs
      - El uso de sus datos para contactar directamente a las empresas
        anunciantes fuera de la plataforma InfoJobs
    Por eso este modo existe SOLO para validar que el scoring produce
    leads de calidad. NUNCA generamos leads para contacto en este modo.
    Todos los registros llevan uso="solo_validacion_interna".

    Credenciales en .env:
      INFOJOBS_CLIENT_ID=...
      INFOJOBS_CLIENT_SECRET=...
    Registro en: https://developer.infojobs.net/
    """

    _BASE_URL  = "https://api.infojobs.net/api/9/offer"
    _PAGE_SIZE = 20

    def __init__(self) -> None:
        client_id     = os.getenv("INFOJOBS_CLIENT_ID", "")
        client_secret = os.getenv("INFOJOBS_CLIENT_SECRET", "")
        if not client_id or not client_secret:
            raise EnvironmentError(
                "Modo 'validation' requiere INFOJOBS_CLIENT_ID y "
                "INFOJOBS_CLIENT_SECRET en .env\n"
                "Regístrate en https://developer.infojobs.net/"
            )
        raw     = f"{client_id}:{client_secret}".encode()
        encoded = base64.b64encode(raw).decode()
        self._headers = {
            "Authorization": f"Basic {encoded}",
            "Content-Type":  "application/json",
        }

    def _search(self, query: str, page: int = 1) -> dict:
        params = {"q": query, "maxResults": self._PAGE_SIZE, "page": page}
        try:
            resp = requests.get(self._BASE_URL, headers=self._headers,
                                params=params, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            logger.error("[job_adapter:validation] Error en '%s': %s", query, str(e)[:100])
            return {}

    def fetch_jobs(
        self,
        queries: list[str],
        location: str,
        max_per_query: int,
    ) -> list[dict[str, Any]]:
        logger.info(
            "[job_adapter:validation] ⚠️  MODO VALIDACIÓN INTERNA — "
            "leads marcados uso=solo_validacion_interna — NO para contacto"
        )
        results: list[dict[str, Any]] = []
        seen: set[str] = set()

        for query in queries:
            data  = self._search(query)
            items = data.get("items", [])[:max_per_query]
            logger.info("  [infojobs-api] '%s' → %d ofertas", query, len(items))

            for item in items:
                url = item.get("link", item.get("id", ""))
                if url in seen:
                    continue
                seen.add(url)

                # Antigüedad de la vacante (señal de urgencia)
                published = item.get("published", "")
                days_open: int | None = None
                if published:
                    try:
                        pub_dt    = datetime.fromisoformat(published.replace("Z", "+00:00"))
                        days_open = (datetime.utcnow().replace(tzinfo=pub_dt.tzinfo) - pub_dt).days
                    except Exception:
                        pass

                # InfoJobs API no expone repost_count directamente — degradamos con None
                results.append(_base_record(
                    title=item.get("title", ""),
                    company=item.get("author", {}).get("name", ""),
                    location=item.get("city", location),
                    description=item.get("requirementsMin", ""),
                    url=url,
                    query=query,
                    source_tag="infojobs_api_validation",
                    uso="solo_validacion_interna",   # ← NUNCA entra en flujo de contacto
                    posted_days_ago=days_open,
                    repost_count=None,               # no disponible en API InfoJobs
                    multiple_openings=int(item.get("vacancies", 1)) > 1,
                    company_sector=item.get("category", {}).get("value", ""),
                ))

        return results


# ── Modo production — agregador con licencia comercial ────────────────────────

class ProductionAggregatorAdapter(JobSourceAdapter):
    """
    Agregador de empleo con licencia comercial (TheirStack, LoopCV, etc.).

    Este es el ÚNICO modo habilitado para generar leads destinados a contacto
    comercial. La licencia del proveedor ampara ese uso y la redistribución
    de los datos.

    Credenciales en .env:
      AGGREGATOR_BASE_URL=https://api.theirstack.com/v1   (o el proveedor elegido)
      AGGREGATOR_API_KEY=...

    Nota: el proveedor concreto está pendiente de confirmar precio/licencia.
    Este adaptador implementa el patrón con TheirStack como ejemplo de
    referencia; ajustar el parseo de respuesta si se elige otro proveedor.
    """

    def __init__(self) -> None:
        self._base_url = os.getenv("AGGREGATOR_BASE_URL", "")
        self._api_key  = os.getenv("AGGREGATOR_API_KEY", "")
        if not self._base_url or not self._api_key:
            raise EnvironmentError(
                "Modo 'production' requiere AGGREGATOR_BASE_URL y "
                "AGGREGATOR_API_KEY en .env\n"
                "Proveedor aún por confirmar — ver ADR en PROJECT_DASHBOARD.md"
            )

    def fetch_jobs(
        self,
        queries: list[str],
        location: str,
        max_per_query: int,
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        seen:    set[str]             = set()
        headers = {"Authorization": f"Bearer {self._api_key}",
                   "Content-Type":  "application/json"}

        for query in queries:
            try:
                resp = requests.post(
                    f"{self._base_url}/jobs/search",
                    headers=headers,
                    json={
                        "job_title_pattern_or": [query],
                        "job_country_code_or":  ["ES"],
                        "job_location_pattern_or": [location] if location else [],
                        "limit": max_per_query,
                        "order_by": [{"desc": True, "field": "first_seen_at"}],
                    },
                    timeout=20,
                )
                resp.raise_for_status()
                data  = resp.json()
                items = data.get("data", [])
                logger.info("  [aggregator] '%s' → %d ofertas", query, len(items))

                for item in items:
                    url = item.get("url", item.get("apply_url", ""))
                    if not url or url in seen:
                        continue
                    seen.add(url)

                    days_open: int | None = None
                    first_seen = item.get("first_seen_at", "")
                    if first_seen:
                        try:
                            fs_dt     = datetime.fromisoformat(first_seen.replace("Z", "+00:00"))
                            days_open = (datetime.utcnow().replace(tzinfo=fs_dt.tzinfo) - fs_dt).days
                        except Exception:
                            pass

                    results.append(_base_record(
                        title=item.get("job_title", ""),
                        company=item.get("company_name", ""),
                        location=item.get("job_location", location),
                        description=item.get("description", "")[:2000],
                        url=url,
                        query=query,
                        source_tag="aggregator_production",
                        uso="comercial",
                        posted_days_ago=days_open,
                        repost_count=item.get("repost_count"),
                        multiple_openings=int(item.get("num_positions", 1)) > 1,
                        company_sector=item.get("company_industry", ""),
                    ))

            except requests.RequestException as e:
                logger.error("[job_adapter:production] Error en '%s': %s",
                             query, str(e)[:100])

        return results


# ── Factory ───────────────────────────────────────────────────────────────────

def create_adapter() -> JobSourceAdapter:
    """
    Crea el adaptador según JOB_SOURCE_MODE.
    Falla con mensaje claro si el modo no está configurado o faltan credenciales.
    NUNCA usa scraping como fallback.
    """
    mode = os.getenv("JOB_SOURCE_MODE", "").strip().lower()

    if not mode:
        raise EnvironmentError(
            "JOB_SOURCE_MODE no definida en .env\n"
            "Valores válidos: mock | validation | production\n"
            "  mock       → datos de ejemplo, sin credenciales (desarrollo/tests)\n"
            "  validation → API oficial InfoJobs (solo validación interna)\n"
            "  production → agregador con licencia comercial (producción)"
        )

    if mode == "mock":
        logger.info("[job_adapter] Modo MOCK — datos de ejemplo")
        return MockJobAdapter()

    if mode == "validation":
        logger.info("[job_adapter] Modo VALIDATION — API InfoJobs (solo uso interno)")
        return InfoJobsValidationAdapter()

    if mode == "production":
        logger.info("[job_adapter] Modo PRODUCTION — agregador con licencia")
        return ProductionAggregatorAdapter()

    raise EnvironmentError(
        f"JOB_SOURCE_MODE='{mode}' no reconocido. "
        "Usa: mock | validation | production"
    )
