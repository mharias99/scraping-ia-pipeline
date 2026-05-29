"""
Google Sheets Exporter — Fase 5.1 (DaaS delivery)

Autenticación con Service Account (sin interacción del usuario).
Setup en 3 pasos:
  1. Crea un proyecto en Google Cloud Console
  2. Activa Google Sheets API + crea Service Account → descarga JSON de credenciales
  3. Comparte tu Google Sheet con el email del Service Account (editor)
  4. Añade al .env:
       GOOGLE_SHEETS_CREDENTIALS_PATH=credentials/service_account.json
       GOOGLE_SHEETS_SPREADSHEET_ID=<id-de-la-hoja>
       GOOGLE_SHEETS_WORKSHEET_NAME=Leads   # opcional, default: Leads
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import gspread
import pandas as pd
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from gspread.exceptions import SpreadsheetNotFound, WorksheetNotFound
from gspread_formatting import (
    CellFormat,
    Color,
    TextFormat,
    format_cell_range,
    set_frozen,
)

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]

# Columnas que se exportan al Sheet (en este orden)
EXPORT_COLUMNS = [
    "lead_score",
    "title",
    "company",
    "location",
    "company_sector",
    "company_size",
    "urgency",
    "automation_signals",
    "lead_reason",
    "contact_email",
    "url",
    "scraped_at",
]

# Colores por score para resaltado visual
SCORE_COLORS: dict[str, Color] = {
    "high":    Color(0.722, 0.961, 0.698),   # verde suave
    "medium":  Color(1.0,   0.953, 0.675),   # amarillo suave
    "low":     Color(1.0,   0.894, 0.800),   # naranja suave
    "discard": Color(0.937, 0.937, 0.937),   # gris claro
}

HEADER_COLOR = Color(0.129, 0.533, 0.753)    # azul corporativo


# ── Autenticación ─────────────────────────────────────────────────────────────

def get_client() -> gspread.Client:
    creds_path = os.getenv("GOOGLE_SHEETS_CREDENTIALS_PATH")
    if not creds_path:
        raise EnvironmentError(
            "GOOGLE_SHEETS_CREDENTIALS_PATH no definida en .env\n"
            "Apunta al JSON de tu Service Account de Google Cloud."
        )
    path = Path(creds_path)
    if not path.exists():
        raise FileNotFoundError(
            f"Credenciales no encontradas: {path}\n"
            "Descarga el JSON desde Google Cloud Console → IAM → Service Accounts."
        )
    creds = Credentials.from_service_account_file(str(path), scopes=SCOPES)
    return gspread.authorize(creds)


# ── Worksheet ─────────────────────────────────────────────────────────────────

def get_or_create_worksheet(
    spreadsheet: gspread.Spreadsheet,
    name: str,
) -> gspread.Worksheet:
    try:
        ws = spreadsheet.worksheet(name)
        logger.info("Hoja existente encontrada: '%s'", name)
        return ws
    except WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=name, rows=1000, cols=len(EXPORT_COLUMNS) + 2)
        logger.info("Hoja nueva creada: '%s'", name)
        return ws


# ── Formato visual ────────────────────────────────────────────────────────────

def _col_letter(idx: int) -> str:
    """Convierte índice 0-based a letra de columna (A, B, ... Z, AA...)."""
    result = ""
    idx += 1
    while idx:
        idx, rem = divmod(idx - 1, 26)
        result = chr(65 + rem) + result
    return result


def apply_formatting(ws: gspread.Worksheet, df: pd.DataFrame) -> None:
    try:
        last_col = _col_letter(len(EXPORT_COLUMNS) - 1)
        total_rows = len(df) + 1  # +1 header

        # Cabecera azul + texto blanco + negrita
        format_cell_range(
            ws, f"A1:{last_col}1",
            CellFormat(
                backgroundColor=HEADER_COLOR,
                textFormat=TextFormat(bold=True, foregroundColor=Color(1, 1, 1)),
            ),
        )

        # Congelar fila de cabecera
        set_frozen(ws, rows=1)

        # Colorear filas según lead_score
        for row_idx, (_, row) in enumerate(df.iterrows(), start=2):
            score = str(row.get("lead_score", "discard")).lower()
            color = SCORE_COLORS.get(score, SCORE_COLORS["discard"])
            format_cell_range(
                ws, f"A{row_idx}:{last_col}{row_idx}",
                CellFormat(backgroundColor=color),
            )

        logger.info("Formato visual aplicado (%d filas)", total_rows)

    except Exception as e:
        # El formato es opcional — no bloquea la exportación
        logger.warning("Formato no aplicado (instala gspread-formatting): %s", e)


# ── Export principal ──────────────────────────────────────────────────────────

def load_latest_leads() -> pd.DataFrame:
    output_dir = Path("data/output")
    csvs = sorted(output_dir.glob("leads_*.csv"), reverse=True)
    if not csvs:
        raise FileNotFoundError(
            "No hay CSV de leads en data/output/. "
            "Ejecuta primero el lead_enricher."
        )
    path = csvs[0]
    logger.info("Cargando leads desde %s", path)
    return pd.read_csv(path)


def prepare_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    # Seleccionar y ordenar columnas de exportación (ignorar las que no existan)
    cols = [c for c in EXPORT_COLUMNS if c in df.columns]
    df = df[cols].copy()

    # Rellenar NaN con cadena vacía para Sheets
    df = df.fillna("")

    # Ordenar HIGH primero
    score_order = {"high": 0, "medium": 1, "low": 2, "discard": 3}
    df["_sort"] = df["lead_score"].map(score_order).fillna(4)
    df = df.sort_values("_sort").drop(columns=["_sort"]).reset_index(drop=True)
    return df


def export_to_sheets(
    df: pd.DataFrame,
    spreadsheet_id: str,
    worksheet_name: str,
    client: gspread.Client,
) -> str:
    try:
        spreadsheet = client.open_by_key(spreadsheet_id)
    except SpreadsheetNotFound:
        raise ValueError(
            f"Spreadsheet no encontrado: {spreadsheet_id}\n"
            "Verifica el ID en la URL de tu Google Sheet y que "
            "hayas compartido la hoja con el email del Service Account."
        )

    ws = get_or_create_worksheet(spreadsheet, worksheet_name)

    # Limpiar contenido previo
    ws.clear()
    logger.info("Hoja limpiada")

    # Escribir cabecera + datos en una sola llamada (más eficiente)
    headers = list(df.columns)
    rows = [headers] + df.values.tolist()
    ws.update(rows, "A1")
    logger.info("Datos escritos: %d filas × %d columnas", len(df), len(headers))

    # Añadir metadato de actualización en celda fuera de rango de datos
    meta_col = _col_letter(len(headers) + 1)
    ws.update_acell(f"{meta_col}1", "Última actualización")
    ws.update_acell(f"{meta_col}2", datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"))

    # Formato visual
    apply_formatting(ws, df)

    url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
    logger.info("Sheet actualizado: %s", url)
    return url


# ── Punto de entrada ──────────────────────────────────────────────────────────

def run_sheets_export() -> str:
    spreadsheet_id = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID")
    if not spreadsheet_id:
        raise EnvironmentError(
            "GOOGLE_SHEETS_SPREADSHEET_ID no definida en .env\n"
            "Copia el ID de la URL de tu Google Sheet: "
            "docs.google.com/spreadsheets/d/<ID>/edit"
        )

    worksheet_name = os.getenv("GOOGLE_SHEETS_WORKSHEET_NAME", "Leads")

    client  = get_client()
    df      = load_latest_leads()
    df      = prepare_dataframe(df)

    high   = len(df[df["lead_score"] == "high"])
    medium = len(df[df["lead_score"] == "medium"])
    logger.info(
        "Exportando %d leads (%d HIGH, %d MEDIUM) → Sheet '%s'",
        len(df), high, medium, worksheet_name,
    )

    url = export_to_sheets(df, spreadsheet_id, worksheet_name, client)

    logger.info(
        "Exportación completa: %d registros en %s",
        len(df), url,
    )
    return url


if __name__ == "__main__":
    sheet_url = run_sheets_export()
    logger.info("Abre tu Sheet: %s", sheet_url)
