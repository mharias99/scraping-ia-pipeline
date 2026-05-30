"""
Seen Tracker — Memoria entre ejecuciones por cliente

Guarda las URLs/IDs de leads ya exportados en data/seen/{client_id}.json
Cada ejecución filtra los registros nuevos y actualiza el fichero.

Garantía: un lead nunca aparece dos veces en el Sheet,
aunque el cliente lo borre manualmente de la hoja.
"""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

SEEN_DIR = Path("data/seen")


def _seen_path(client_id: str) -> Path:
    return SEEN_DIR / f"{client_id}.json"


def load_seen(client_id: str) -> set[str]:
    path = _seen_path(client_id)
    if not path.exists():
        return set()
    with open(path, encoding="utf-8") as f:
        return set(json.load(f))


def save_seen(client_id: str, seen: set[str]) -> None:
    SEEN_DIR.mkdir(parents=True, exist_ok=True)
    with open(_seen_path(client_id), "w", encoding="utf-8") as f:
        json.dump(sorted(seen), f, ensure_ascii=False)


def _url_key(record: dict[str, Any], pipeline_type: str) -> str:
    """Extrae la clave única del registro según el tipo de pipeline."""
    if pipeline_type == "car_arbitrage":
        return record.get("url") or f"{record.get('title','')}|{record.get('price','')}"
    if pipeline_type == "digital_audit":
        return record.get("maps_url") or record.get("name", "")
    # b2b_leads
    return record.get("url") or f"{record.get('company','')}|{record.get('title','')}"


def filter_new(
    records: list[dict[str, Any]],
    client_id: str,
    pipeline_type: str = "b2b_leads",
) -> tuple[list[dict[str, Any]], set[str]]:
    """
    Filtra los registros que ya se han exportado previamente.

    Returns:
        (nuevos_records, seen_actualizado)
    """
    seen = load_seen(client_id)
    new_records = []
    new_keys: set[str] = set()

    for record in records:
        key = _url_key(record, pipeline_type)
        if key and key not in seen:
            new_records.append(record)
            new_keys.add(key)

    total = len(records)
    skipped = total - len(new_records)
    if skipped:
        logger.info("[seen_tracker] %d leads ya vistos omitidos | %d nuevos",
                    skipped, len(new_records))
    else:
        logger.info("[seen_tracker] Primera ejecución — %d leads nuevos", len(new_records))

    return new_records, seen | new_keys


def commit(client_id: str, seen: set[str]) -> None:
    """Persiste el seen actualizado. Llamar solo si el export fue exitoso."""
    prev_count = len(load_seen(client_id))
    save_seen(client_id, seen)
    logger.info("[seen_tracker] %d leads en memoria (%d nuevos)",
                len(seen), len(seen) - prev_count)


def reset(client_id: str) -> None:
    """Borra la memoria del cliente. Útil para reiniciar una demo."""
    path = _seen_path(client_id)
    if path.exists():
        path.unlink()
        logger.info("[seen_tracker] Memoria de '%s' borrada", client_id)
