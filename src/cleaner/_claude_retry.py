"""
Utilidades de retry compartidas para llamadas a la API de Anthropic.
Usadas por lead_enricher.py y digital_enricher.py.
"""
import logging
import time
from typing import Any, Callable

import anthropic

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


def call_with_retry(
    fn: Callable[[], list[dict[str, Any]]],
    context: str = "batch",
    attempt: int = 1,
) -> list[dict[str, Any]]:
    """
    Llama a `fn()` con retry exponencial ante RateLimitError.

    Args:
        fn:      Función sin argumentos que ejecuta la llamada a la API.
        context: Descripción del contexto para el log (ej. "lead batch 3/10").
        attempt: Número de intento actual (uso interno para recursión).

    Returns:
        Lista de resultados, o lista vacía si se superan los reintentos.
    """
    try:
        return fn()
    except anthropic.RateLimitError:
        if attempt > MAX_RETRIES:
            logger.error("[claude_retry] Rate limit: max retries alcanzado en %s", context)
            return []
        wait = 2 ** attempt
        logger.warning("[claude_retry] Rate limit en %s — reintentando en %ds (intento %d/%d)",
                       context, wait, attempt, MAX_RETRIES)
        time.sleep(wait)
        return call_with_retry(fn, context, attempt + 1)
    except anthropic.BadRequestError as e:
        if "credit balance is too low" in str(e):
            raise RuntimeError(
                "Anthropic API: saldo insuficiente. "
                "Recarga en https://console.anthropic.com/settings/billing"
            ) from e
        logger.error("[claude_retry] BadRequestError en %s: %s", context, e)
        raise
    except anthropic.APIError as e:
        logger.error("[claude_retry] APIError en %s: %s", context, type(e).__name__)
        raise
