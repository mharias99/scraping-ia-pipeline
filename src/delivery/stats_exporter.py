"""
Exporta métricas de ejecución a data/web/stats.json para el dashboard Next.js.
Cada pipeline actualiza solo su clave — no sobreescribe las demás.
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_STATS_PATH = Path("data/web/stats.json")


def export_pipeline_stats(pipeline_type: str, stats: dict[str, Any]) -> None:
    """
    Merge-escribe la sección `pipeline_type` en data/web/stats.json.
    Si el archivo ya existe, solo actualiza la clave del pipeline ejecutado.
    """
    _STATS_PATH.parent.mkdir(parents=True, exist_ok=True)

    existing: dict[str, Any] = {}
    if _STATS_PATH.exists():
        try:
            with open(_STATS_PATH, encoding="utf-8") as f:
                existing = json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("[stats] stats.json corrupto, se sobreescribirá: %s", exc)

    existing[pipeline_type] = stats
    existing["last_run_type"] = pipeline_type
    existing["updated_at"] = datetime.now(timezone.utc).isoformat()

    with open(_STATS_PATH, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

    logger.info("[stats] data/web/stats.json actualizado [%s]", pipeline_type)
