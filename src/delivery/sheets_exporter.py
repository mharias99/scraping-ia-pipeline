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
from datetime import date, datetime
from pathlib import Path
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
    format_cell_ranges,
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

# ── Columnas por tipo de pipeline ────────────────────────────────────────────

EXPORT_COLUMNS = [          # b2b_leads (default)
    "lead_score", "title", "company", "location", "company_sector",
    "company_size", "urgency", "automation_signals", "lead_reason",
    "outreach_email", "contact_email", "url", "scraped_at",
]

EXPORT_COLUMNS_CARS = [     # car_arbitrage
    "opportunity", "title", "price", "market_median", "price_delta_pct",
    "year", "km", "location", "phone", "url", "model_query", "scraped_at",
]

EXPORT_COLUMNS_DIGITAL = [  # digital_audit V2
    "priority", "name", "category", "digital_score", "maps_score", "web_score",
    "rating", "review_count", "web_status", "web_https", "web_booking",
    "web_pixel_meta", "web_pixel_ga", "phone", "address",
    "weaknesses", "call_script", "maps_url", "scraped_at",
]

_COLUMNS_BY_TYPE: dict[str, list[str]] = {
    "b2b_leads":    EXPORT_COLUMNS,
    "car_arbitrage": EXPORT_COLUMNS_CARS,
    "digital_audit": EXPORT_COLUMNS_DIGITAL,
}

# ── Colores por score ─────────────────────────────────────────────────────────

# Reutilizados para todos los pipelines: HIGH/high=verde, MEDIUM/medium=amarillo, etc.
SCORE_COLORS: dict[str, Color] = {
    "high":         Color(0.722, 0.961, 0.698),
    "HIGH":         Color(0.722, 0.961, 0.698),
    "medium":       Color(1.0,   0.953, 0.675),
    "MEDIUM":       Color(1.0,   0.953, 0.675),
    "low":          Color(1.0,   0.894, 0.800),
    "LOW":          Color(1.0,   0.894, 0.800),
    "discard":      Color(0.937, 0.937, 0.937),
    "NORMAL":       Color(0.95,  0.95,  0.95),
    "SOBREVALORADO": Color(0.937, 0.937, 0.937),
    "UNKNOWN":      Color(0.937, 0.937, 0.937),
}

HEADER_COLOR = Color(0.129, 0.533, 0.753)

# Opciones del dropdown de Estado (gestionado por el cliente, nunca sobreescrito)
ESTADO_OPTIONS = [
    "🔵 Pendiente",
    "📞 Interesado",
    "🔄 Seguimiento",
    "❌ No interesado",
    "✅ Cerrado",
]

# Colores para la columna Estado (resaltan el progreso de la llamada)
ESTADO_COLORS: dict[str, Color] = {
    "🔵 Pendiente":      Color(0.898, 0.937, 1.0),    # azul muy suave
    "📞 Interesado":     Color(0.722, 0.961, 0.698),  # verde
    "🔄 Seguimiento":    Color(1.0,   0.953, 0.675),  # amarillo
    "❌ No interesado":  Color(0.937, 0.937, 0.937),  # gris
    "✅ Cerrado":         Color(0.569, 0.820, 0.698),  # verde oscuro
}


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
    num_cols: int | None = None,
) -> gspread.Worksheet:
    cols = (num_cols or len(EXPORT_COLUMNS)) + 2
    try:
        ws = spreadsheet.worksheet(name)
        logger.info("Hoja existente encontrada: '%s'", name)
        return ws
    except WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=name, rows=1000, cols=cols)
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


def apply_formatting(
    ws: gspread.Worksheet,
    df: pd.DataFrame,
    score_col: str = "lead_score",
) -> None:
    try:
        last_col   = _col_letter(len(df.columns) - 1)
        total_rows = len(df) + 1

        format_cell_range(
            ws, f"A1:{last_col}1",
            CellFormat(
                backgroundColor=HEADER_COLOR,
                textFormat=TextFormat(bold=True, foregroundColor=Color(1, 1, 1)),
            ),
        )
        set_frozen(ws, rows=1)

        fallback = SCORE_COLORS.get("discard", Color(0.9, 0.9, 0.9))
        row_formats = [
            (
                f"A{row_idx}:{last_col}{row_idx}",
                CellFormat(backgroundColor=SCORE_COLORS.get(
                    str(row.get(score_col, "")).strip(),
                    fallback,
                )),
            )
            for row_idx, (_, row) in enumerate(df.iterrows(), start=2)
        ]
        format_cell_ranges(ws, row_formats)
        logger.info("Formato visual aplicado (%d filas)", total_rows)

    except (gspread.exceptions.APIError, gspread.exceptions.GSpreadException, ValueError) as e:
        logger.warning("Formato visual no aplicado: %s — %s", type(e).__name__, e)


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


def prepare_dataframe(
    df: pd.DataFrame,
    pipeline_type: str = "b2b_leads",
) -> pd.DataFrame:
    export_cols = _COLUMNS_BY_TYPE.get(pipeline_type, EXPORT_COLUMNS)
    cols = [c for c in export_cols if c in df.columns]
    df = df[cols].copy().fillna("")

    # Ordenar según el campo de prioridad del pipeline
    if pipeline_type == "b2b_leads":
        order = {"high": 0, "medium": 1, "low": 2, "discard": 3}
        df["_sort"] = df.get("lead_score", pd.Series(dtype=str)).map(order).fillna(4)
    elif pipeline_type == "car_arbitrage":
        order = {"HIGH": 0, "MEDIUM": 1, "NORMAL": 2, "SOBREVALORADO": 3, "UNKNOWN": 4}
        df["_sort"] = df.get("opportunity", pd.Series(dtype=str)).map(order).fillna(4)
    elif pipeline_type == "digital_audit":
        order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        df["_sort"] = df.get("priority", pd.Series(dtype=str)).map(order).fillna(3)
    else:
        df["_sort"] = 0

    df = df.sort_values("_sort").drop(columns=["_sort"]).reset_index(drop=True)
    return df


def export_to_sheets(
    df: pd.DataFrame,
    spreadsheet_id: str,
    worksheet_name: str,
    client: gspread.Client,
    pipeline_type: str = "b2b_leads",
) -> str:
    try:
        spreadsheet = client.open_by_key(spreadsheet_id)
    except SpreadsheetNotFound:
        raise ValueError(
            f"Spreadsheet no encontrado: {spreadsheet_id}\n"
            "Verifica el ID en la URL de tu Google Sheet y que "
            "hayas compartido la hoja con el email del Service Account."
        )

    ws = get_or_create_worksheet(spreadsheet, worksheet_name, num_cols=len(df.columns))
    ws.clear()
    logger.info("Hoja limpiada")

    headers = list(df.columns)
    rows = [headers] + df.values.tolist()
    ws.update(rows, "A1")
    logger.info("Datos escritos: %d filas × %d columnas", len(df), len(headers))

    meta_col = _col_letter(len(headers))
    ws.update_acell(f"{meta_col}1", "Última actualización")
    ws.update_acell(f"{meta_col}2", datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"))

    # Campo de color según el pipeline
    score_col_map = {
        "b2b_leads":    "lead_score",
        "car_arbitrage": "opportunity",
        "digital_audit": "priority",
    }
    apply_formatting(ws, df, score_col=score_col_map.get(pipeline_type, "lead_score"))

    url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
    logger.info("Sheet actualizado: %s", url)
    return url


# ── Dropdown Estado ──────────────────────────────────────────────────────────

def _set_estado_dropdown(
    spreadsheet: gspread.Spreadsheet,
    ws: gspread.Worksheet,
    first_data_row: int,
    last_row: int,
) -> None:
    """Aplica validación de dropdown a la columna A (Estado) para las filas de datos."""
    try:
        sheet_id = ws._properties["sheetId"]
        requests = [{
            "setDataValidation": {
                "range": {
                    "sheetId":       sheet_id,
                    "startRowIndex": first_data_row - 1,  # 0-based
                    "endRowIndex":   last_row,
                    "startColumnIndex": 0,
                    "endColumnIndex":   1,
                },
                "rule": {
                    "condition": {
                        "type":   "ONE_OF_LIST",
                        "values": [{"userEnteredValue": v} for v in ESTADO_OPTIONS],
                    },
                    "showCustomUi": True,
                    "strict":       False,
                },
            }
        }]
        spreadsheet.batch_update({"requests": requests})
    except Exception as e:
        logger.warning("Dropdown Estado no aplicado: %s", str(e)[:80])


# ── Append incremental ────────────────────────────────────────────────────────

def append_new_leads(
    df: pd.DataFrame,
    spreadsheet_id: str,
    worksheet_name: str,
    gc: gspread.Client,
    pipeline_type: str = "b2b_leads",
) -> tuple[str, int]:
    """
    Añade solo los nuevos leads al Sheet sin tocar filas existentes.

    - Columna A: Estado (dropdown, gestionado por el cliente)
    - Columnas B…N: datos del pipeline
    - Última columna: fecha_alta

    Returns:
        (url_del_sheet, n_filas_añadidas)
    """
    try:
        spreadsheet = gc.open_by_key(spreadsheet_id)
    except SpreadsheetNotFound:
        raise ValueError(
            f"Spreadsheet no encontrado: {spreadsheet_id}. "
            "Verifica que lo hayas compartido con el Service Account."
        )

    # Columnas de datos (sin Estado ni fecha_alta, que añadimos nosotros)
    export_cols = _COLUMNS_BY_TYPE.get(pipeline_type, EXPORT_COLUMNS)
    data_cols   = [c for c in export_cols if c in df.columns]
    df_data     = df[data_cols].copy().fillna("")

    # Cabecera completa: Estado + datos + fecha_alta
    headers = ["Estado"] + data_cols + ["fecha_alta"]

    ws = get_or_create_worksheet(spreadsheet, worksheet_name, num_cols=len(headers))

    # ── ¿Hoja nueva o existente? ──────────────────────────────────────────────
    existing = ws.get_all_values()
    is_new   = len(existing) == 0

    if is_new:
        ws.append_row(headers, value_input_option="RAW")
        # Formato cabecera
        last_col = _col_letter(len(headers) - 1)
        try:
            format_cell_range(
                ws, f"A1:{last_col}1",
                CellFormat(
                    backgroundColor=HEADER_COLOR,
                    textFormat=TextFormat(bold=True, foregroundColor=Color(1, 1, 1)),
                ),
            )
            set_frozen(ws, rows=1)
        except Exception:
            pass
        first_new_row = 2
    else:
        first_new_row = len(existing) + 1

    if df_data.empty:
        logger.info("[sheets] Sin leads nuevos para añadir")
        return f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}", 0

    # ── Construir filas nuevas ────────────────────────────────────────────────
    today = date.today().isoformat()
    new_rows = [
        ["🔵 Pendiente"] + row.tolist() + [today]
        for _, row in df_data.iterrows()
    ]

    ws.append_rows(new_rows, value_input_option="RAW")
    logger.info("[sheets] %d filas añadidas (total hoja: %d)",
                len(new_rows), first_new_row + len(new_rows) - 2)

    # ── Colorear filas nuevas según score ─────────────────────────────────────
    score_col_map = {
        "b2b_leads":     "lead_score",
        "car_arbitrage": "opportunity",
        "digital_audit": "priority",
    }
    score_col = score_col_map.get(pipeline_type, "lead_score")
    fallback  = SCORE_COLORS.get("discard", Color(0.9, 0.9, 0.9))
    last_col  = _col_letter(len(headers) - 1)

    try:
        row_formats = []
        for i, (_, row) in enumerate(df_data.iterrows()):
            r = first_new_row + i
            score_val = str(row.get(score_col, "")).strip()
            row_formats.append((
                f"A{r}:{last_col}{r}",
                CellFormat(backgroundColor=SCORE_COLORS.get(score_val, fallback)),
            ))
        format_cell_ranges(ws, row_formats)
    except Exception as e:
        logger.warning("[sheets] Coloreado parcial: %s", str(e)[:80])

    # ── Dropdown Estado para las filas nuevas ─────────────────────────────────
    last_row = first_new_row + len(new_rows) - 1
    _set_estado_dropdown(spreadsheet, ws, first_new_row, last_row)

    url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
    logger.info("[sheets] Sheet actualizado: %s", url)
    return url, len(new_rows)


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
