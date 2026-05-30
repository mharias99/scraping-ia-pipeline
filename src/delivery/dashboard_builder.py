"""
Dashboard Builder — Pestañas '📊 Dashboard' especializadas por pipeline.

Tres dashboards completamente distintos, cada uno con los KPIs, métricas y
secciones que hacen sentido para su vertical de negocio:

  · B2B Leads     → embudo, score, sectores, outreach, leads diarios
  · Car Arbitrage → margen potencial, mejores modelos, precio vs mercado, contacs
  · Digital Audit → score digital, debilidades, call-ready list, sectores

Usa _Batch para enviar todas las escrituras en 2 llamadas API (raw + formulas)
evitando el error 429 de cuota de Google Sheets.

Compatible con gspread 6.x — update(values, range_name).
"""

import logging
import time

import gspread
from gspread.exceptions import WorksheetNotFound
from gspread_formatting import (
    CellFormat, Color, TextFormat,
    format_cell_range, format_cell_ranges, set_frozen,
)

logger = logging.getLogger(__name__)

DASHBOARD_TAB = "📊 Dashboard"

# ── Paleta ───────────────────────────────────────────────────────────────────
_W   = Color(1, 1, 1)

# Fondos de sección
_NAVY    = Color(0.086, 0.153, 0.290)   # azul marino oscuro — encabezados generales
_INDIGO  = Color(0.200, 0.220, 0.600)   # indigo — B2B
_AMBER_D = Color(0.500, 0.320, 0.050)   # ámbar oscuro — Cars
_TEAL_D  = Color(0.050, 0.380, 0.400)   # teal oscuro — Digital

# Fills de celdas de valor
_GREEN   = Color(0.722, 0.961, 0.698)
_YELLOW  = Color(1.000, 0.953, 0.675)
_ORANGE  = Color(1.000, 0.850, 0.700)
_RED_L   = Color(1.000, 0.894, 0.800)
_GRAY    = Color(0.937, 0.937, 0.937)
_BLUE_L  = Color(0.870, 0.920, 1.000)
_DARK    = Color(0.180, 0.180, 0.180)
_RED_B   = Color(0.780, 0.100, 0.100)


# ── Batch writer ──────────────────────────────────────────────────────────────

class _Batch:
    """Acumula escrituras y las envía en 2 llamadas API (raw + USER_ENTERED)."""

    def __init__(self, ws: gspread.Worksheet) -> None:
        self._ws = ws
        self._raw:     list[dict] = []
        self._formula: list[dict] = []

    def put(self, rng: str, values: list, formula: bool = False) -> None:
        (self._formula if formula else self._raw).append(
            {"range": rng, "values": values}
        )

    def flush(self) -> None:
        if self._raw:
            self._ws.batch_update(self._raw)
        if self._formula:
            if self._raw:
                time.sleep(1.5)
            self._ws.batch_update(self._formula, raw=False)


# ── Helpers de formato ────────────────────────────────────────────────────────

def _hdr(bg: Color, txt: Color = _W, size: int = 10, bold: bool = True) -> CellFormat:
    return CellFormat(
        backgroundColor=bg,
        textFormat=TextFormat(bold=bold, fontSize=size, foregroundColor=txt),
        horizontalAlignment="CENTER",
        verticalAlignment="MIDDLE",
    )

def _val_fmt(bg: Color, size: int = 20, bold: bool = True) -> CellFormat:
    return CellFormat(
        backgroundColor=bg,
        textFormat=TextFormat(bold=bold, fontSize=size,
                              foregroundColor=Color(0.1, 0.1, 0.1)),
        horizontalAlignment="CENTER",
        verticalAlignment="MIDDLE",
    )

def _merge(sp: gspread.Spreadsheet, sid: int,
           r1: int, c1: int, r2: int, c2: int) -> None:
    try:
        sp.batch_update({"requests": [{"mergeCells": {
            "range": {"sheetId": sid,
                      "startRowIndex": r1, "endRowIndex": r2,
                      "startColumnIndex": c1, "endColumnIndex": c2},
            "mergeType": "MERGE_ALL",
        }}]})
    except Exception:
        pass

def _chart(sp: gspread.Spreadsheet, spec: dict) -> None:
    try:
        sp.batch_update({"requests": [{"addChart": {"chart": spec}}]})
    except Exception as e:
        logger.warning("[dashboard] Gráfico omitido: %s", str(e)[:80])


# ── Fórmulas (separador ';' para locale español) ──────────────────────────────

def _sp(d: str, col: str, val: str) -> str:
    return f"=SUMPRODUCT(('{d}'!{col}2:{col}10000=\"{val}\")*1)"

def _sp2(d: str, c1: str, v1: str, c2: str, v2: str) -> str:
    return (
        f"=SUMPRODUCT(('{d}'!{c1}2:{c1}10000=\"{v1}\")"
        f"*('{d}'!{c2}2:{c2}10000=\"{v2}\"))"
    )

def _total(d: str) -> str:
    return f"=IFERROR(COUNTA('{d}'!A:A)-1;0)"

def _avg_if(d: str, crit_col: str, crit_val: str, val_col: str) -> str:
    return (
        f"=IFERROR(ROUND(AVERAGEIF('{d}'!{crit_col}:{crit_col};"
        f"\"{crit_val}\";'{d}'!{val_col}:{val_col});1);0)"
    )

def _sum_if(d: str, crit_col: str, crit_val: str, val_col: str) -> str:
    return f"=IFERROR(ROUND(SUMIF('{d}'!{crit_col}:{crit_col};\"{crit_val}\";'{d}'!{val_col}:{val_col});0);0)"

def _sum_delta_high(d: str, score_col: str, price_col: str, median_col: str) -> str:
    """Suma (mediana-precio) para filas HIGH."""
    return (
        f"=IFERROR(ROUND(SUMPRODUCT("
        f"('{d}'!{score_col}2:{score_col}10000=\"HIGH\")*"
        f"('{d}'!{median_col}2:{median_col}10000-'{d}'!{price_col}2:{price_col}10000)"
        f");0);0)"
    )

def _tasa_contacto(d: str) -> str:
    tot  = f"COUNTA('{d}'!A:A)-1"
    pend = f"SUMPRODUCT(('{d}'!A2:A10000=\"🔵 Pendiente\")*1)"
    return f"=IFERROR(ROUND(({tot}-{pend})/MAX({tot};1)*100;1)&\"%\";\"0%\")"

def _filter_high(d: str, col: str, score_col: str, score_val: str, fallback: str = "") -> str:
    return (
        f"=IFERROR(FILTER('{d}'!{col}2:{col}10000;"
        f"('{d}'!{score_col}2:{score_col}10000=\"{score_val}\")*"
        f"('{d}'!A2:A10000=\"🔵 Pendiente\"));"
        f"\"{fallback}\")"
    )

def _query_top(d: str, label_col: str, count_col: str,
               where_col: str, where_val: str, n: int = 10) -> str:
    rng = f"'{d}'!A2:U"
    return (
        f"=IFERROR(QUERY({rng};"
        f"\"SELECT {label_col}, COUNT({count_col}) "
        f"WHERE {count_col}='{where_val}' "
        f"GROUP BY {label_col} "
        f"ORDER BY COUNT({count_col}) DESC "
        f"LIMIT {n} "
        f"LABEL {label_col} '', COUNT({count_col}) ''\";0);"
        f"\"Sin datos\")"
    )

def _countif_col(d: str, col: str, val: str) -> str:
    return f"=COUNTIF('{d}'!{col}:{col};\"{val}\")"

def _pct_of_total(d: str, col: str, val: str) -> str:
    n  = f"COUNTIF('{d}'!{col}:{col};\"{val}\")"
    tot = f"MAX(COUNTA('{d}'!A:A)-1;1)"
    return f"=IFERROR(ROUND({n}/{tot}*100;1)&\"%\";\"0%\")"


# ── Infraestructura común ─────────────────────────────────────────────────────

def _setup_tab(
    spreadsheet: gspread.Spreadsheet,
    rows: int = 80, cols: int = 16,
) -> tuple[gspread.Worksheet, int]:
    try:
        old = spreadsheet.worksheet(DASHBOARD_TAB)
        spreadsheet.del_worksheet(old)
        logger.info("[dashboard] Tab eliminado para regenerar")
    except WorksheetNotFound:
        pass
    ws  = spreadsheet.add_worksheet(title=DASHBOARD_TAB, rows=rows, cols=cols)
    sid = (ws._properties or {}).get("sheetId", 0)
    try:
        spreadsheet.batch_update({"requests": [{"updateSheetProperties": {
            "properties": {"sheetId": sid, "index": 0}, "fields": "index",
        }}]})
    except Exception:
        pass
    return ws, sid


def _estado_section(
    b: _Batch, sp: gspread.Spreadsheet, sid: int,
    d: str, start_row: int, accent: Color,
) -> int:
    """Tabla de estados del pipeline — igual para los 3 verticales. Retorna next_row."""
    r = start_row
    b.put(f"A{r}", [["ESTADO DEL PIPELINE"]])
    b.put(f"A{r+1}:C{r+1}", [["Estado", "Leads", "%"]])
    estados = ["🔵 Pendiente", "📞 Interesado", "🔄 Seguimiento",
               "❌ No interesado", "✅ Cerrado"]
    rows = [[e, _sp(d, "A", e),
             f"=IFERROR(ROUND(B{r+2+i}/B{r+7}*100;1)&\"%\";\"0%\")"]
            for i, e in enumerate(estados)]
    rows.append(["TOTAL", _total(d), "100%"])
    b.put(f"A{r+2}:C{r+7}", rows, formula=True)
    _merge(sp, sid, r-1, 0, r, 4)
    return r + 9


# ═══════════════════════════════════════════════════════════════════════════════
# B2B LEADS — dashboard completo
# Columnas: A=Estado B=lead_score C=title D=company E=location F=company_sector
#           G=size H=urgency I=signals J=reason K=outreach L=contact M=url
#           N=scraped O=fecha_alta
# ═══════════════════════════════════════════════════════════════════════════════

def _build_b2b(
    b: _Batch, sp: gspread.Spreadsheet, sid: int, d: str, ws: gspread.Worksheet
) -> None:
    acc = _INDIGO

    # ── TÍTULO ────────────────────────────────────────────────────────────────
    b.put("A1:L1", [["🎯 B2B LEADS — CAPTACIÓN DE CLIENTES DE AUTOMATIZACIÓN"] + [""]*11])
    _merge(sp, sid, 0, 0, 1, 12)

    # ── KPI ROW 1: volumen ────────────────────────────────────────────────────
    b.put("A3:K3", [["TOTAL LEADS", "", "HIGH SIN LLAMAR", "",
                     "MEDIUM SIN LLAMAR", "", "INTERESADOS", "",
                     "SEGUIMIENTO", "", "CERRADOS"]])
    b.put("A4:K4", [[
        _total(d), "",
        _sp2(d, "B", "high", "A", "🔵 Pendiente"), "",
        _sp2(d, "B", "medium", "A", "🔵 Pendiente"), "",
        _sp(d, "A", "📞 Interesado"), "",
        _sp(d, "A", "🔄 Seguimiento"), "",
        _sp(d, "A", "✅ Cerrado"),
    ]], formula=True)

    # ── KPI ROW 2: calidad ────────────────────────────────────────────────────
    b.put("A5:K5", [["TASA CONTACTO", "", "HIGH URGENTES", "",
                     "% HIGH del total", "", "LEADS NUEVOS HOY", "",
                     "SECTORES ÚNICOS", "", ""]])
    b.put("A6:K6", [[
        _tasa_contacto(d), "",
        _sp2(d, "H", "urgent", "B", "high"), "",
        f"=IFERROR(ROUND({_sp(d,'B','high')[1:]}/MAX({_total(d)[1:]};1)*100;1)&\"%\";\"0%\")", "",
        f"=COUNTIF('{d}'!O:O;TEXT(TODAY();\"YYYY-MM-DD\"))", "",
        f"=IFERROR(SUMPRODUCT(1/COUNTIF('{d}'!F2:F10000;'{d}'!F2:F10000)*('{d}'!F2:F10000<>\"\"));0)", "",
        "",
    ]], formula=True)

    # ── ESTADO + SCORE (fila 8) ───────────────────────────────────────────────
    r_est = _estado_section(b, sp, sid, d, 8, acc)

    b.put("E8", [["DISTRIBUCIÓN LEAD SCORE"]])
    b.put("E9:F9", [["Score", "Leads"]])
    scores = [("high", "HIGH ⚡"), ("medium", "MEDIUM"), ("low", "LOW"), ("discard", "DESCARTADO")]
    b.put("E10:F13", [[lbl, _sp(d, "B", sc)] for sc, lbl in scores], formula=True)
    _merge(sp, sid, 7, 4, 8, 8)

    b.put("H8", [["URGENTES (necesitan acción hoy)"]])
    b.put("H9:I9", [["Urgencia", "HIGH"]])
    b.put("H10:I12", [
        ["🔥 Urgent",  _sp2(d, "H", "urgent", "B", "high")],
        ["⏳ Normal",  _sp2(d, "H", "normal", "B", "high")],
        ["❓ Unknown", _sp2(d, "H", "unknown", "B", "high")],
    ], formula=True)
    _merge(sp, sid, 7, 7, 8, 11)

    # ── TOP SECTORES (fila 18) ────────────────────────────────────────────────
    b.put("A18", [["TOP 8 SECTORES CON MÁS HIGH"]])
    b.put("A19:B19", [["Sector", "Leads HIGH"]])
    b.put("A20", [[_query_top(d, "F", "B", "B", "high", 8)]], formula=True)
    _merge(sp, sid, 17, 0, 18, 4)

    # ── LEADS POR DÍA (fila 18, col D) ───────────────────────────────────────
    b.put("D18", [["LEADS CAPTADOS — ÚLTIMOS 14 DÍAS"]])
    b.put("D19:E19", [["Fecha", "Leads"]])
    date_rows = []
    for off in range(13, -1, -1):
        row = 20 + (13 - off)
        df_ = f"=TEXT(TODAY()-{off};\"YYYY-MM-DD\")" if off else "=TEXT(TODAY();\"YYYY-MM-DD\")"
        date_rows.append([df_, f"=COUNTIF('{d}'!O:O;D{row})"])
    b.put("D20:E33", date_rows, formula=True)
    _merge(sp, sid, 17, 3, 18, 8)

    # ── HIGH PENDIENTES — LLAMAR HOY (fila 37) ───────────────────────────────
    b.put("A37", [["⚡ HIGH PENDIENTES — LLAMAR HOY (score + sin contactar)"]])
    b.put("A38:F38", [["Empresa", "Puesto oferta", "Ubicación",
                       "Email prospección (preview)", "URL oferta", "Añadido"]])
    col_map = [("A39","D","Sin leads HIGH pendientes"), ("B39","C",""),
               ("C39","E",""), ("D39","K",""), ("E39","M",""), ("F39","O","")]
    for cell, col, fb in col_map:
        b.put(cell, [[_filter_high(d, col, "B", "high", fb)]], formula=True)
    _merge(sp, sid, 36, 0, 37, 10)

    # ── Gráficos ──────────────────────────────────────────────────────────────
    _chart(sp, {
        "spec": {
            "title": "Estado del Pipeline",
            "pieChart": {
                "legendPosition": "RIGHT_LEGEND",
                "domain":  {"sourceRange": {"sources": [{"sheetId": sid, "startRowIndex": 9, "endRowIndex": 14, "startColumnIndex": 0, "endColumnIndex": 1}]}},
                "series": {"sourceRange": {"sources": [{"sheetId": sid, "startRowIndex": 9, "endRowIndex": 14, "startColumnIndex": 1, "endColumnIndex": 2}]}},
            },
        },
        "position": {"overlayPosition": {
            "anchorCell": {"sheetId": sid, "rowIndex": 7, "columnIndex": 11},
            "widthPixels": 380, "heightPixels": 220,
        }},
    })
    _chart(sp, {
        "spec": {
            "title": "Lead Score Mix",
            "pieChart": {
                "legendPosition": "RIGHT_LEGEND",
                "domain":  {"sourceRange": {"sources": [{"sheetId": sid, "startRowIndex": 9, "endRowIndex": 13, "startColumnIndex": 4, "endColumnIndex": 5}]}},
                "series": {"sourceRange": {"sources": [{"sheetId": sid, "startRowIndex": 9, "endRowIndex": 13, "startColumnIndex": 5, "endColumnIndex": 6}]}},
            },
        },
        "position": {"overlayPosition": {
            "anchorCell": {"sheetId": sid, "rowIndex": 7, "columnIndex": 14},
            "widthPixels": 320, "heightPixels": 220,
        }},
    })
    _chart(sp, {
        "spec": {
            "title": "Leads captados por día",
            "basicChart": {
                "chartType": "LINE",
                "legendPosition": "NO_LEGEND",
                "axis": [{"position": "BOTTOM_AXIS"}, {"position": "LEFT_AXIS"}],
                "domains": [{"domain": {"sourceRange": {"sources": [{"sheetId": sid, "startRowIndex": 19, "endRowIndex": 33, "startColumnIndex": 3, "endColumnIndex": 4}]}}}],
                "series": [{"series": {"sourceRange": {"sources": [{"sheetId": sid, "startRowIndex": 19, "endRowIndex": 33, "startColumnIndex": 4, "endColumnIndex": 5}]}}, "targetAxis": "LEFT_AXIS"}],
                "headerCount": 0,
            },
        },
        "position": {"overlayPosition": {
            "anchorCell": {"sheetId": sid, "rowIndex": 17, "columnIndex": 8},
            "widthPixels": 420, "heightPixels": 220,
        }},
    })

    # ── Formato ───────────────────────────────────────────────────────────────
    fmts = [
        ("A1",    _hdr(acc, size=13)),
        ("A3:K3", _hdr(acc, size=9)),
        ("A4",    _val_fmt(_GREEN, 22)), ("C4", _val_fmt(_GREEN, 22)),
        ("E4",    _val_fmt(_YELLOW, 22)), ("G4", _val_fmt(_BLUE_L, 18)),
        ("I4",    _val_fmt(_YELLOW, 18)), ("K4", _val_fmt(_GREEN, 18)),
        ("A5:K5", _hdr(_DARK, size=9)),
        ("A6",    CellFormat(textFormat=TextFormat(bold=True, fontSize=14), horizontalAlignment="CENTER")),
        ("C6",    _val_fmt(_RED_L, 18)), ("E6", _val_fmt(_BLUE_L, 16)),
        ("G6",    _val_fmt(_GREEN, 18)),
        ("A8",    _hdr(_DARK)), ("E8", _hdr(_DARK)), ("H8", _hdr(_DARK)),
        ("A9:C9", _hdr(acc, size=9)), ("E9:F9", _hdr(acc, size=9)),
        ("H9:I9", _hdr(acc, size=9)),
        ("A15:C15", CellFormat(backgroundColor=_GRAY,
                               textFormat=TextFormat(bold=True),
                               horizontalAlignment="CENTER")),
        ("A18",   _hdr(_DARK)), ("D18", _hdr(_DARK)),
        ("A19:B19", _hdr(acc, size=9)), ("D19:E19", _hdr(acc, size=9)),
        ("A37",   _hdr(_RED_B, size=12)),
        ("A38:F38", _hdr(acc, size=9)),
    ]
    score_colors = [_GREEN, _YELLOW, _RED_L, _GRAY]
    for i, c in enumerate(score_colors):
        fmts.append((f"E{10+i}", CellFormat(backgroundColor=c)))
    format_cell_ranges(ws, fmts)
    set_frozen(ws, rows=1)


# ═══════════════════════════════════════════════════════════════════════════════
# CAR ARBITRAGE — dashboard
# Columnas: A=Estado B=opportunity C=title D=price E=market_median
#           F=price_delta_pct G=year H=km I=location J=phone K=url
#           L=model_query M=scraped_at N=fecha_alta
# ═══════════════════════════════════════════════════════════════════════════════

def _build_cars(
    b: _Batch, sp: gspread.Spreadsheet, sid: int, d: str, ws: gspread.Worksheet
) -> None:
    acc = _AMBER_D

    b.put("A1:L1", [["🚗 ARBITRAJE DE VEHÍCULOS — OPORTUNIDADES DE COMPRA"] + [""]*11])
    _merge(sp, sid, 0, 0, 1, 12)

    # ── KPI ROW 1: oportunidades ──────────────────────────────────────────────
    b.put("A3:K3", [["TOTAL ANUNCIOS", "", "HIGH (≥15% bajo)", "",
                     "MEDIUM (8-14%)", "", "MARGEN TOTAL HIGH €", "",
                     "DELTA MEDIO HIGH", "", "PENDIENTES CONTACTAR"]])
    b.put("A4:K4", [[
        _total(d), "",
        _sp(d, "B", "HIGH"), "",
        _sp(d, "B", "MEDIUM"), "",
        _sum_delta_high(d, "B", "D", "E"), "",
        _avg_if(d, "B", "HIGH", "E") + " - " + _avg_if(d, "B", "HIGH", "D"),
        "",
        _sp2(d, "B", "HIGH", "A", "🔵 Pendiente"),
    ]], formula=True)

    # ── KPI ROW 2: métricas ───────────────────────────────────────────────────
    b.put("A5:K5", [["SOBREVALORADOS", "", "% HIGH del total", "",
                     "INTERESADOS", "", "SEGUIMIENTO", "", "CERRADOS", "", ""]])
    b.put("A6:K6", [[
        _sp(d, "B", "SOBREVALORADO"), "",
        f"=IFERROR(ROUND({_sp(d,'B','HIGH')[1:]}/MAX({_total(d)[1:]};1)*100;1)&\"%\";\"0%\")", "",
        _sp(d, "A", "📞 Interesado"), "",
        _sp(d, "A", "🔄 Seguimiento"), "",
        _sp(d, "A", "✅ Cerrado"), "", "",
    ]], formula=True)

    # ── ESTADO + SCORE OPORTUNIDAD (fila 8) ───────────────────────────────────
    r_est = _estado_section(b, sp, sid, d, 8, acc)

    b.put("E8", [["CLASIFICACIÓN OPORTUNIDAD"]])
    b.put("E9:F9", [["Tipo", "Anuncios"]])
    opp_rows = [
        ["HIGH ⚡ (≥15% bajo mercado)",    _sp(d, "B", "HIGH")],
        ["MEDIUM (8–14% bajo mercado)",    _sp(d, "B", "MEDIUM")],
        ["NORMAL (precio de mercado)",     _sp(d, "B", "NORMAL")],
        ["SOBREVALORADO (>precio mercado)",_sp(d, "B", "SOBREVALORADO")],
        ["UNKNOWN (muestra insuficiente)", _sp(d, "B", "UNKNOWN")],
    ]
    b.put("E10:F14", opp_rows, formula=True)
    _merge(sp, sid, 7, 4, 8, 11)

    # ── TOP MODELOS HIGH (fila 18) ────────────────────────────────────────────
    b.put("A18", [["TOP MODELOS — más oportunidades HIGH"]])
    b.put("A19:B19", [["Modelo buscado", "HIGH"]])
    b.put("A20", [[_query_top(d, "L", "B", "B", "HIGH", 7)]], formula=True)
    _merge(sp, sid, 17, 0, 18, 4)

    # ── ANÁLISIS DE PRECIO (fila 18, col D) ───────────────────────────────────
    b.put("D18", [["ANÁLISIS DE PRECIO · oportunidades HIGH"]])
    b.put("D19:F19", [["Métrica", "Valor (€)", "Detalle"]])
    b.put("D20:F24", [
        ["Precio medio HIGH",    _avg_if(d, "B", "HIGH", "D"),    "precio real anunciado"],
        ["Precio mercado medio", _avg_if(d, "B", "HIGH", "E"),    "mediana del grupo"],
        ["Delta medio (ahorro)", f"=IFERROR(F21-F20;0)",           "€ por debajo mercado"],
        ["Coste total si compras todos HIGH",
         _sum_if(d, "B", "HIGH", "D"),                              "inversión total"],
        ["Valor mercado total HIGH",
         _sum_if(d, "B", "HIGH", "E"),                              "valor si vendes a precio mercado"],
    ], formula=True)
    _merge(sp, sid, 17, 3, 18, 10)

    # ── HIGH PENDIENTES — CONTACTAR HOY (fila 37) ─────────────────────────────
    b.put("A37", [["⚡ HIGH PENDIENTES — CONTACTAR HOY (≥15% bajo precio mercado)"]])
    b.put("A38:F38", [["Vehículo", "Precio €", "Precio Mercado €",
                       "Ahorro %", "Ubicación", "Teléfono vendedor"]])
    col_map = [("A39","C","Sin oportunidades HIGH pendientes"), ("B39","D",""),
               ("C39","E",""), ("D39","F",""), ("E39","I",""), ("F39","J","")]
    for cell, col, fb in col_map:
        b.put(cell, [[_filter_high(d, col, "B", "HIGH", fb)]], formula=True)
    _merge(sp, sid, 36, 0, 37, 10)

    # ── Gráficos ──────────────────────────────────────────────────────────────
    _chart(sp, {
        "spec": {
            "title": "Estado del Pipeline",
            "pieChart": {
                "legendPosition": "RIGHT_LEGEND",
                "domain":  {"sourceRange": {"sources": [{"sheetId": sid, "startRowIndex": 9, "endRowIndex": 14, "startColumnIndex": 0, "endColumnIndex": 1}]}},
                "series": {"sourceRange": {"sources": [{"sheetId": sid, "startRowIndex": 9, "endRowIndex": 14, "startColumnIndex": 1, "endColumnIndex": 2}]}},
            },
        },
        "position": {"overlayPosition": {
            "anchorCell": {"sheetId": sid, "rowIndex": 7, "columnIndex": 11},
            "widthPixels": 360, "heightPixels": 220,
        }},
    })
    _chart(sp, {
        "spec": {
            "title": "Clasificación de Oportunidades",
            "pieChart": {
                "legendPosition": "RIGHT_LEGEND",
                "domain":  {"sourceRange": {"sources": [{"sheetId": sid, "startRowIndex": 9, "endRowIndex": 14, "startColumnIndex": 4, "endColumnIndex": 5}]}},
                "series": {"sourceRange": {"sources": [{"sheetId": sid, "startRowIndex": 9, "endRowIndex": 14, "startColumnIndex": 5, "endColumnIndex": 6}]}},
            },
        },
        "position": {"overlayPosition": {
            "anchorCell": {"sheetId": sid, "rowIndex": 7, "columnIndex": 14},
            "widthPixels": 360, "heightPixels": 220,
        }},
    })

    # ── Formato ───────────────────────────────────────────────────────────────
    fmts = [
        ("A1",    _hdr(acc, size=13)),
        ("A3:K3", _hdr(acc, size=9)),
        ("A4",    _val_fmt(_GRAY, 20)), ("C4", _val_fmt(_GREEN, 22)),
        ("E4",    _val_fmt(_YELLOW, 22)), ("G4", _val_fmt(_GREEN, 20)),
        ("I4",    _val_fmt(_YELLOW, 18)), ("K4", _val_fmt(_BLUE_L, 18)),
        ("A5:K5", _hdr(_DARK, size=9)),
        ("A6",    _val_fmt(_RED_L, 16)), ("E6", _val_fmt(_BLUE_L, 16)),
        ("A8",    _hdr(_DARK)), ("E8", _hdr(_DARK)),
        ("A9:C9", _hdr(acc, size=9)), ("E9:F9", _hdr(acc, size=9)),
        ("A18",   _hdr(_DARK)), ("D18", _hdr(_DARK)),
        ("A19:B19", _hdr(acc, size=9)), ("D19:F19", _hdr(acc, size=9)),
        ("A37",   _hdr(_RED_B, size=12)),
        ("A38:F38", _hdr(acc, size=9)),
    ]
    opp_colors = [_GREEN, _YELLOW, _GRAY, _RED_L, _GRAY]
    for i, c in enumerate(opp_colors):
        fmts.append((f"E{10+i}", CellFormat(backgroundColor=c)))
    format_cell_ranges(ws, fmts)
    set_frozen(ws, rows=1)


# ═══════════════════════════════════════════════════════════════════════════════
# DIGITAL AUDIT — dashboard
# Columnas: A=Estado B=priority C=name D=category E=digital_score
#           F=maps_score G=web_score H=rating I=review_count J=web_status
#           K=web_https L=web_booking M=web_pixel_meta N=web_pixel_ga
#           O=phone P=address Q=weaknesses R=call_script S=maps_url
#           T=scraped_at U=fecha_alta
# ═══════════════════════════════════════════════════════════════════════════════

def _build_digital(
    b: _Batch, sp: gspread.Spreadsheet, sid: int, d: str, ws: gspread.Worksheet
) -> None:
    acc = _TEAL_D

    b.put("A1:L1", [["📡 AUDITORÍA DIGITAL DE PYMEs — LEADS PARA AGENCIAS DE MARKETING"] + [""]*11])
    _merge(sp, sid, 0, 0, 1, 12)

    # ── KPI ROW 1: volumen ────────────────────────────────────────────────────
    b.put("A3:K3", [["TOTAL AUDITADOS", "", "HIGH (dolor máx)", "",
                     "MEDIUM", "", "SIN WEB", "",
                     "SIN HTTPS", "", "SIN RESERVAS"]])
    b.put("A4:K4", [[
        _total(d), "",
        _sp(d, "B", "HIGH"), "",
        _sp(d, "B", "MEDIUM"), "",
        _sp(d, "J", "no_web"), "",
        f"=SUMPRODUCT(('{d}'!K2:K10000=FALSE)*1)", "",
        f"=SUMPRODUCT(('{d}'!L2:L10000=FALSE)*1)",
    ]], formula=True)

    # ── KPI ROW 2: scores ─────────────────────────────────────────────────────
    b.put("A5:K5", [["SCORE DIGITAL MEDIO HIGH", "", "SCORE MAPS MEDIO", "",
                     "% HIGH DEL TOTAL", "", "CON TELÉFONO", "",
                     "SIN PIXEL META/GA", "", "INTERESADOS"]])
    b.put("A6:K6", [[
        _avg_if(d, "B", "HIGH", "E"), "",
        f"=IFERROR(ROUND(AVERAGE('{d}'!F2:F10000);1);0)", "",
        f"=IFERROR(ROUND({_sp(d,'B','HIGH')[1:]}/MAX({_total(d)[1:]};1)*100;1)&\"%\";\"0%\")", "",
        f"=SUMPRODUCT(('{d}'!O2:O10000<>\"\")*1)", "",
        f"=SUMPRODUCT(('{d}'!M2:M10000=FALSE)*('{d}'!N2:N10000=FALSE)*1)", "",
        _sp(d, "A", "📞 Interesado"),
    ]], formula=True)

    # ── ESTADO + PRIORIDAD (fila 8) ───────────────────────────────────────────
    r_est = _estado_section(b, sp, sid, d, 8, acc)

    b.put("E8", [["DISTRIBUCIÓN DE PRIORIDAD"]])
    b.put("E9:G9", [["Prioridad", "Negocios", "Score medio"]])
    b.put("E10:G12", [
        ["HIGH — dolor máximo",   _sp(d, "B", "HIGH"),   _avg_if(d, "B", "HIGH", "E")],
        ["MEDIUM — dolor medio",  _sp(d, "B", "MEDIUM"), _avg_if(d, "B", "MEDIUM", "E")],
        ["LOW — presencia OK",    _sp(d, "B", "LOW"),    _avg_if(d, "B", "LOW", "E")],
    ], formula=True)
    _merge(sp, sid, 7, 4, 8, 10)

    b.put("H8", [["DEBILIDADES MÁS FRECUENTES"]])
    b.put("H9:I9", [["Debilidad", "Afectados"]])
    b.put("H10:I15", [
        ["Sin web registrada",       _sp(d, "J", "no_web")],
        ["Web caída",                _sp(d, "J", "down")],
        ["Sin HTTPS",                f"=SUMPRODUCT(('{d}'!K2:K10000=FALSE)*1)"],
        ["Sin reservas online",      f"=SUMPRODUCT(('{d}'!L2:L10000=FALSE)*1)"],
        ["Sin píxel Meta/GA",        f"=SUMPRODUCT(('{d}'!M2:M10000=FALSE)*('{d}'!N2:N10000=FALSE)*1)"],
        ["Revisar manualmente",      _sp(d, "J", "revisar_manual")],
    ], formula=True)
    _merge(sp, sid, 7, 7, 8, 11)

    # ── TOP SECTORES (fila 18) ────────────────────────────────────────────────
    b.put("A18", [["TOP 8 SECTORES — mayor dolor digital"]])
    b.put("A19:B19", [["Sector", "Negocios HIGH"]])
    b.put("A20", [[_query_top(d, "D", "B", "B", "HIGH", 8)]], formula=True)
    _merge(sp, sid, 17, 0, 18, 4)

    # ── COBERTURA WEB (fila 18, col D) ────────────────────────────────────────
    b.put("D18", [["COBERTURA DE PRESENCIA WEB"]])
    b.put("D19:F19", [["Indicador", "N", "%"]])
    b.put("D20:F25", [
        ["Sin web",          _sp(d, "J", "no_web"),     _pct_of_total(d, "J", "no_web")],
        ["Web caída",        _sp(d, "J", "down"),       _pct_of_total(d, "J", "down")],
        ["Sin HTTPS",        f"=SUMPRODUCT(('{d}'!K2:K10000=FALSE)*1)",
                             f"=IFERROR(ROUND(SUMPRODUCT(('{d}'!K2:K10000=FALSE)*1)/MAX({_total(d)[1:]};1)*100;1)&\"%\";\"0%\")"],
        ["Sin reservas",     f"=SUMPRODUCT(('{d}'!L2:L10000=FALSE)*1)",
                             f"=IFERROR(ROUND(SUMPRODUCT(('{d}'!L2:L10000=FALSE)*1)/MAX({_total(d)[1:]};1)*100;1)&\"%\";\"0%\")"],
        ["Sin pixel Meta/GA",f"=SUMPRODUCT(('{d}'!M2:M10000=FALSE)*('{d}'!N2:N10000=FALSE)*1)",
                             f"=IFERROR(ROUND(SUMPRODUCT(('{d}'!M2:M10000=FALSE)*('{d}'!N2:N10000=FALSE)*1)/MAX({_total(d)[1:]};1)*100;1)&\"%\";\"0%\")"],
        ["Con teléfono",     f"=SUMPRODUCT(('{d}'!O2:O10000<>\"\")*1)",
                             f"=IFERROR(ROUND(SUMPRODUCT(('{d}'!O2:O10000<>\"\")*1)/MAX({_total(d)[1:]};1)*100;1)&\"%\";\"0%\")"],
    ], formula=True)
    _merge(sp, sid, 17, 3, 18, 9)

    # ── HIGH PENDIENTES — LLAMAR HOY (fila 37) ───────────────────────────────
    b.put("A37", [["⚡ HIGH PENDIENTES — LLAMAR HOY (call_script listo)"]])
    b.put("A38:F38", [["Negocio", "Categoría", "Score Digital",
                       "Teléfono", "Script apertura (preview)", "Google Maps"]])
    col_map = [("A39","C","Sin negocios HIGH pendientes"), ("B39","D",""),
               ("C39","E",""), ("D39","O",""), ("E39","R",""), ("F39","S","")]
    for cell, col, fb in col_map:
        b.put(cell, [[_filter_high(d, col, "B", "HIGH", fb)]], formula=True)
    _merge(sp, sid, 36, 0, 37, 10)

    # ── Gráficos ──────────────────────────────────────────────────────────────
    _chart(sp, {
        "spec": {
            "title": "Estado del Pipeline",
            "pieChart": {
                "legendPosition": "RIGHT_LEGEND",
                "domain":  {"sourceRange": {"sources": [{"sheetId": sid, "startRowIndex": 9, "endRowIndex": 14, "startColumnIndex": 0, "endColumnIndex": 1}]}},
                "series": {"sourceRange": {"sources": [{"sheetId": sid, "startRowIndex": 9, "endRowIndex": 14, "startColumnIndex": 1, "endColumnIndex": 2}]}},
            },
        },
        "position": {"overlayPosition": {
            "anchorCell": {"sheetId": sid, "rowIndex": 7, "columnIndex": 11},
            "widthPixels": 360, "heightPixels": 220,
        }},
    })
    _chart(sp, {
        "spec": {
            "title": "Distribución de Prioridad",
            "pieChart": {
                "legendPosition": "RIGHT_LEGEND",
                "domain":  {"sourceRange": {"sources": [{"sheetId": sid, "startRowIndex": 9, "endRowIndex": 12, "startColumnIndex": 4, "endColumnIndex": 5}]}},
                "series": {"sourceRange": {"sources": [{"sheetId": sid, "startRowIndex": 9, "endRowIndex": 12, "startColumnIndex": 5, "endColumnIndex": 6}]}},
            },
        },
        "position": {"overlayPosition": {
            "anchorCell": {"sheetId": sid, "rowIndex": 7, "columnIndex": 14},
            "widthPixels": 360, "heightPixels": 220,
        }},
    })

    # ── Formato ───────────────────────────────────────────────────────────────
    fmts = [
        ("A1",    _hdr(acc, size=13)),
        ("A3:K3", _hdr(acc, size=9)),
        ("A4",    _val_fmt(_GRAY, 20)), ("C4", _val_fmt(_GREEN, 22)),
        ("E4",    _val_fmt(_YELLOW, 22)), ("G4", _val_fmt(_RED_L, 20)),
        ("I4",    _val_fmt(_RED_L, 20)), ("K4", _val_fmt(_RED_L, 20)),
        ("A5:K5", _hdr(_DARK, size=9)),
        ("A6",    _val_fmt(_GREEN, 16)), ("C6", _val_fmt(_BLUE_L, 14)),
        ("A8",    _hdr(_DARK)), ("E8", _hdr(_DARK)), ("H8", _hdr(_DARK)),
        ("A9:C9", _hdr(acc, size=9)), ("E9:G9", _hdr(acc, size=9)),
        ("H9:I9", _hdr(acc, size=9)),
        ("A18",   _hdr(_DARK)), ("D18", _hdr(_DARK)),
        ("A19:B19", _hdr(acc, size=9)), ("D19:F19", _hdr(acc, size=9)),
        ("A37",   _hdr(_RED_B, size=12)),
        ("A38:F38", _hdr(acc, size=9)),
    ]
    pri_colors = [_GREEN, _YELLOW, _GRAY]
    for i, c in enumerate(pri_colors):
        fmts.append((f"E{10+i}", CellFormat(backgroundColor=c)))
    format_cell_ranges(ws, fmts)
    set_frozen(ws, rows=1)


# ── Orquestador ───────────────────────────────────────────────────────────────

def build_dashboard(
    spreadsheet: gspread.Spreadsheet,
    data_sheet_name: str,
    pipeline_type: str = "b2b_leads",
) -> None:
    d   = data_sheet_name
    ws, sid = _setup_tab(spreadsheet, rows=90, cols=18)
    logger.info("[dashboard] Creando '📊 Dashboard' [%s]...", pipeline_type)

    b = _Batch(ws)
    if pipeline_type == "b2b_leads":
        _build_b2b(b, spreadsheet, sid, d, ws)
    elif pipeline_type == "car_arbitrage":
        _build_cars(b, spreadsheet, sid, d, ws)
    elif pipeline_type == "digital_audit":
        _build_digital(b, spreadsheet, sid, d, ws)
    else:
        logger.warning("[dashboard] Tipo desconocido: %s", pipeline_type)
        return

    b.flush()
    logger.info("[dashboard] '📊 Dashboard' creado [%s]", pipeline_type)


# ── Puntos de entrada ─────────────────────────────────────────────────────────

def build_b2b_dashboard(
    spreadsheet_id: str, data_sheet_name: str, gc: gspread.Client,
) -> None:
    build_dashboard(gc.open_by_key(spreadsheet_id), data_sheet_name, "b2b_leads")

def build_cars_dashboard(
    spreadsheet_id: str, data_sheet_name: str, gc: gspread.Client,
) -> None:
    build_dashboard(gc.open_by_key(spreadsheet_id), data_sheet_name, "car_arbitrage")

def build_digital_dashboard(
    spreadsheet_id: str, data_sheet_name: str, gc: gspread.Client,
) -> None:
    build_dashboard(gc.open_by_key(spreadsheet_id), data_sheet_name, "digital_audit")
