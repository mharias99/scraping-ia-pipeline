import fs   from "fs";
import path from "path";

// ── Tipos ──────────────────────────────────────────────────────────
export interface B2BStats {
  offers_extracted: number;
  leads_qualified:  number;
  leads_high:       number;
  leads_medium:     number;
  leads_low:        number;
  leads_discard:    number;
  pipeline_time_s:  number;
  sources: {
    indeed:   { offers: number };
    infojobs: { offers: number };
  };
}

export interface CarsStats {
  ads_analyzed:         number;
  opportunities_high:   number;
  opportunities_medium: number;
  avg_delta_eur:        number;
  pipeline_time_s:      number;
}

export interface DigitalStats {
  businesses_audited: number;
  clients_high:       number;
  clients_medium:     number;
  pct_no_web:         number;
  pct_no_booking:     number;
  pipeline_time_s:    number;
}

export interface PipelineStats {
  updated_at:    string | null;
  last_run_type: string | null;
  b2b_leads:     B2BStats;
  car_arbitrage: CarsStats;
  digital_audit: DigitalStats;
}

// ── Defaults (se usan si el JSON no existe o le falta una clave) ───
const DEFAULTS: PipelineStats = {
  updated_at:    null,
  last_run_type: null,
  b2b_leads: {
    offers_extracted: 50,
    leads_qualified:  31,
    leads_high:       11,
    leads_medium:     13,
    leads_low:        7,
    leads_discard:    19,
    pipeline_time_s:  98,
    sources: {
      indeed:   { offers: 38 },
      infojobs: { offers: 12 },
    },
  },
  car_arbitrage: {
    ads_analyzed:         350,
    opportunities_high:   52,
    opportunities_medium: 87,
    avg_delta_eur:        3200,
    pipeline_time_s:      0,
  },
  digital_audit: {
    businesses_audited: 125,
    clients_high:       42,
    clients_medium:     36,
    pct_no_web:         68,
    pct_no_booking:     71,
    pipeline_time_s:    0,
  },
};

// ── Loader (solo para Server Components) ─────────────────────────
// process.cwd() en Next.js dev = project-ui/
// El JSON vive en ../data/web/stats.json
const STATS_PATH = path.join(process.cwd(), "..", "data", "web", "stats.json");

export function loadStats(): PipelineStats {
  try {
    const raw  = fs.readFileSync(STATS_PATH, "utf-8");
    const data = JSON.parse(raw) as Partial<PipelineStats>;
    return {
      updated_at:    data.updated_at    ?? null,
      last_run_type: data.last_run_type ?? null,
      b2b_leads:     { ...DEFAULTS.b2b_leads,     ...(data.b2b_leads     ?? {}) },
      car_arbitrage: { ...DEFAULTS.car_arbitrage, ...(data.car_arbitrage ?? {}) },
      digital_audit: { ...DEFAULTS.digital_audit, ...(data.digital_audit ?? {}) },
    };
  } catch {
    // stats.json no existe todavía → datos demo
    return DEFAULTS;
  }
}

// ── Helpers de formato ────────────────────────────────────────────
export function formatUpdatedAt(isoDate: string | null): string {
  if (!isoDate) return "Demo · sin ejecución real aún";
  const d = new Date(isoDate);
  const diffMs  = Date.now() - d.getTime();
  const diffMin = Math.floor(diffMs / 60_000);
  if (diffMin < 1)   return "hace menos de 1 minuto";
  if (diffMin < 60)  return `hace ${diffMin} minuto${diffMin === 1 ? "" : "s"}`;
  const diffH = Math.floor(diffMin / 60);
  if (diffH < 24)    return `hace ${diffH} hora${diffH === 1 ? "" : "s"}`;
  return d.toLocaleDateString("es-ES", { day: "2-digit", month: "short", year: "numeric" });
}
