"""
CRM Exporter — Fase 5.2
Genera CSVs listos para importar en HubSpot y Pipedrive
sin necesidad de API keys — el cliente los importa manualmente o vía Zapier.
"""

import logging
from datetime import date
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path("data/output")

# ── Mappings de columnas ──────────────────────────────────────────────────────

HUBSPOT_COLUMNS = {
    "company":        "Company Name",
    "title":          "Job Title Detected",
    "location":       "City",
    "company_sector": "Industry",
    "lead_score":     "Lead Status",
    "lead_reason":    "Description",
    "automation_signals": "Notes",
    "urgency":        "Priority",
    "contact_email":  "Email",
    "url":            "Website",
}

PIPEDRIVE_COLUMNS = {
    "company":        "Organization Name",
    "location":       "Address",
    "company_sector": "Label",
    "lead_score":     "Stage",
    "lead_reason":    "Note",
    "contact_email":  "Contact Email",
    "url":            "Source URL",
}

HUBSPOT_LEAD_STATUS = {
    "high":    "New",
    "medium":  "Open",
    "low":     "In Progress",
    "discard": "Unqualified",
}

PIPEDRIVE_STAGE = {
    "high":    "Qualified",
    "medium":  "Contact Made",
    "low":     "Demo Scheduled",
    "discard": "Lost",
}


# ── Transformaciones ──────────────────────────────────────────────────────────

def _load_leads(min_score: str = "medium") -> pd.DataFrame:
    csvs = sorted(OUTPUT_DIR.glob("leads_*.csv"), reverse=True)
    if not csvs:
        raise FileNotFoundError("No hay leads en data/output/. Ejecuta el pipeline primero.")
    df = pd.read_csv(csvs[0])
    score_order = {"high": 0, "medium": 1, "low": 2, "discard": 3}
    min_val = score_order.get(min_score, 1)
    return df[df["lead_score"].map(score_order).fillna(3) <= min_val].copy()


def export_hubspot(min_score: str = "medium") -> Path:
    df = _load_leads(min_score)

    out = pd.DataFrame()
    for src, dst in HUBSPOT_COLUMNS.items():
        if src in df.columns:
            out[dst] = df[src]

    # Mapear lead_score → HubSpot Lead Status
    if "Lead Status" in out.columns:
        out["Lead Status"] = out["Lead Status"].map(HUBSPOT_LEAD_STATUS).fillna("New")

    # Columnas extra que HubSpot espera
    out["Create Date"]    = date.today().isoformat()
    out["Lifecycle Stage"] = "Lead"

    path = OUTPUT_DIR / f"hubspot_{date.today().strftime('%Y%m%d')}.csv"
    out.to_csv(path, index=False, encoding="utf-8")
    logger.info("HubSpot CSV: %s (%d contactos)", path, len(out))
    return path


def export_pipedrive(min_score: str = "medium") -> Path:
    df = _load_leads(min_score)

    out = pd.DataFrame()
    for src, dst in PIPEDRIVE_COLUMNS.items():
        if src in df.columns:
            out[dst] = df[src]

    # Deal Title: "Automatización backoffice · <Empresa>"
    if "Organization Name" in out.columns:
        out["Deal Title"] = "Automatización backoffice · " + out["Organization Name"].fillna("")

    # Stage según lead_score
    if "Stage" in out.columns:
        out["Stage"] = out["Stage"].map(PIPEDRIVE_STAGE).fillna("Contact Made")

    # Valor estimado del deal (placeholder)
    out["Deal Value"] = ""
    out["Currency"]   = "EUR"
    out["Owner"]      = ""

    path = OUTPUT_DIR / f"pipedrive_{date.today().strftime('%Y%m%d')}.csv"
    out.to_csv(path, index=False, encoding="utf-8")
    logger.info("Pipedrive CSV: %s (%d deals)", path, len(out))
    return path


def run_crm_export(
    min_score: str = "medium",
    pipeline_type: str = "b2b_leads",
) -> dict[str, Path]:
    """Solo genera CSVs de CRM para el pipeline B2B (tiene columnas HubSpot/Pipedrive)."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if pipeline_type != "b2b_leads":
        logger.info("[crm] Export CRM omitido para pipeline '%s' (solo B2B)", pipeline_type)
        empty = OUTPUT_DIR / f"crm_skip_{pipeline_type}_{date.today().strftime('%Y%m%d')}.txt"
        empty.write_text(f"CRM export no aplica para {pipeline_type}\n")
        return {"hubspot": empty, "pipedrive": empty}
    hs  = export_hubspot(min_score)
    pd_ = export_pipedrive(min_score)
    return {"hubspot": hs, "pipedrive": pd_}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    paths = run_crm_export(min_score="medium")
    for crm, path in paths.items():
        logger.info("%s → %s", crm.upper(), path)
