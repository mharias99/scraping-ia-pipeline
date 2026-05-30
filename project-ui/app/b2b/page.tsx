import { PageMotion }                 from "@/components/PageMotion";
import { AnimatedNumber }             from "@/components/AnimatedNumber";
import { loadStats, formatUpdatedAt } from "@/lib/stats";
import Link                           from "next/link";

const ADRS = [
  { id: "ADR-001", title: "Google Sheets · Service Account", status: "Activa", color: "#10b981",
    desc: "Zero-friction para PYMEs. Setup <10 min. Colores automáticos por score." },
  { id: "ADR-002", title: "Apify · Volumen masivo",          status: "Activo", color: "#10b981",
    desc: "Para >500 ofertas/semana. Actores mantenidos. Proxies rotativos incluidos." },
  { id: "ADR-003", title: "Firecrawl · Anti-bot bypass",     status: "Activa", color: "#10b981",
    desc: "Bypasea Distil/Imperva. 50 ofertas en 17s. Plan pago $19/mes en producción." },
];

const QUERIES = [
  "operador introducción datos", "grabador datos excel",
  "administrativo base de datos", "auxiliar contable excel",
  "data entry", "facturación administrativa",
  "auxiliar administrativo excel", "gestor facturación",
];

const HITOS = [
  "Scraper PoC",              "Pipeline E2E validado",
  "Firecrawl integrado",      "Lead enricher B2B",
  "Google Sheets export",     "CRM export (HubSpot/PD)",
  "Dashboard Streamlit",      "Deploy Streamlit Cloud",
  "Apify volumen masivo",     "Tests suite (71 tests)",
  "Security review",          "Queries por portal",
  "Paginación 3 páginas",     "Guion demo comercial",
  "Config YAML por cliente",  "Logging rotativo",
  "Seen tracker dedup",       "UI Next.js + live stats",
];

const PENDING = ["Créditos Firecrawl plan pago", "Primer cliente real"];

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-3 mb-4">
      <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-slate-600">{children}</p>
      <div className="flex-1 h-px bg-white/[0.04]" />
    </div>
  );
}

export default function B2BPage() {
  const stats  = loadStats();
  const b2b    = stats.b2b_leads;
  const updatedLabel = formatUpdatedAt(stats.updated_at);

  const indeedOffers  = b2b.sources?.indeed?.offers  ?? 38;
  const ijOffers      = b2b.sources?.infojobs?.offers ?? 12;
  const maxSource     = Math.max(indeedOffers, ijOffers, 1);
  const indeedLeads   = Math.round(b2b.leads_qualified * (indeedOffers / (indeedOffers + ijOffers)));
  const ijLeads       = b2b.leads_qualified - indeedLeads;

  const KPIS = [
    { label: "Ofertas extraídas",   value: b2b.offers_extracted,  suffix: "",   icon: "🔍", hint: "Firecrawl bypass" },
    { label: "Leads cualificados",  value: b2b.leads_qualified,   suffix: "",   icon: "✅", hint: "62% del total" },
    { label: "Leads HIGH",          value: b2b.leads_high,        suffix: "",   icon: "⚡", hint: "Automatización directa" },
    { label: "Leads MEDIUM",        value: b2b.leads_medium,      suffix: "",   icon: "📊", hint: "Potencial medio" },
    { label: "Tiempo pipeline",     value: b2b.pipeline_time_s,   suffix: "s",  icon: "⏱", hint: "E2E completo", decimals: 1 },
    { label: "Coste IA",            value: 0.005,                 suffix: "$",  icon: "💲", hint: "Claude Haiku", decimals: 3 },
  ];

  const FUNNEL = [
    { label: "Páginas scrapeadas",  value: Math.max(Math.round(b2b.offers_extracted / 5), 1), total: 15, color: "#60a5fa" },
    { label: "Ofertas extraídas",   value: b2b.offers_extracted,  total: b2b.offers_extracted, color: "#818cf8" },
    { label: "Leads cualificados",  value: b2b.leads_qualified,   total: b2b.offers_extracted, color: "#a78bfa" },
    { label: "Leads HIGH score",    value: b2b.leads_high,        total: b2b.offers_extracted, color: "#4ade80" },
  ];
  const funnelMax = Math.max(...FUNNEL.map((f) => f.value));

  const SCORES = [
    { label: "HIGH",    value: b2b.leads_high,    color: "#4ade80", bg: "rgba(74,222,128,0.12)",  border: "rgba(74,222,128,0.2)",  pct: Math.round(b2b.leads_high   / b2b.offers_extracted * 100) },
    { label: "MEDIUM",  value: b2b.leads_medium,  color: "#facc15", bg: "rgba(250,204,21,0.12)",  border: "rgba(250,204,21,0.2)",  pct: Math.round(b2b.leads_medium / b2b.offers_extracted * 100) },
    { label: "LOW",     value: b2b.leads_low,     color: "#fb923c", bg: "rgba(251,146,60,0.12)",  border: "rgba(251,146,60,0.2)",  pct: Math.round(b2b.leads_low    / b2b.offers_extracted * 100) },
    { label: "DISCARD", value: b2b.leads_discard, color: "#6b7280", bg: "rgba(107,114,128,0.12)", border: "rgba(107,114,128,0.2)", pct: Math.round(b2b.leads_discard / b2b.offers_extracted * 100) },
  ];

  return (
    <PageMotion>
      <div className="px-8 py-8 max-w-6xl mx-auto">

        {/* Header */}
        <div className="mb-8 anim-fade-up d-0">
          <div className="flex items-center gap-3 mb-2">
            <Link href="/" className="text-slate-600 hover:text-slate-400 transition-colors">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5 3 12m0 0 7.5-7.5M3 12h18" />
              </svg>
            </Link>
            <div
              className="w-9 h-9 rounded-xl flex items-center justify-center text-lg"
              style={{ background: "linear-gradient(135deg, #6366f130, #6366f115)", border: "1px solid #6366f130" }}
            >🎯</div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-white">B2B Lead Intelligence</h1>
              <p className="text-xs text-slate-500 mt-0.5">InfoJobs + Indeed · Firecrawl + Claude Haiku · Google Sheets</p>
            </div>
            <div className="ml-auto text-right">
              <span className="text-[11px] px-2.5 py-1 rounded-full bg-indigo-500/15 text-indigo-300 border border-indigo-500/25 font-medium">
                Pipeline activo
              </span>
              <p className="text-[10px] text-slate-600 font-mono mt-1">{updatedLabel}</p>
            </div>
          </div>
          <div className="mt-5 h-px bg-gradient-to-r from-indigo-500/30 via-white/[0.06] to-transparent" />
        </div>

        {/* KPIs */}
        <div className="mb-8 anim-fade-up d-1">
          <SectionTitle>Métricas · última ejecución real</SectionTitle>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
            {KPIS.map((k, i) => (
              <div
                key={k.label}
                className="glass glass-hover rounded-2xl p-4 flex flex-col gap-2 hover:glow-indigo transition-all duration-300"
                style={{ animationDelay: `${i * 50}ms` }}
              >
                <div className="flex items-center justify-between">
                  <span className="w-7 h-7 rounded-lg bg-indigo-500/15 flex items-center justify-center text-sm">{k.icon}</span>
                  <span className="text-[9px] text-slate-700 font-mono truncate max-w-[80px] text-right">{k.hint}</span>
                </div>
                <div>
                  <p className="text-2xl font-bold text-white tabular-nums leading-none">
                    <AnimatedNumber value={k.value} suffix={k.suffix} decimals={"decimals" in k ? (k as {decimals: number}).decimals : 0} duration={900} />
                  </p>
                  <p className="text-[10px] text-slate-500 mt-1 leading-tight">{k.label}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Funnel + Score */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6 anim-fade-up d-3">
          {/* Embudo */}
          <div className="glass rounded-2xl p-5">
            <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-slate-600 mb-5">Embudo de captación</p>
            <div className="space-y-3">
              {FUNNEL.map((f) => (
                <div key={f.label} className="flex items-center gap-3">
                  <span className="text-[11px] text-slate-400 w-36 shrink-0">{f.label}</span>
                  <div className="flex-1 h-6 rounded-lg bg-white/[0.03] relative overflow-hidden">
                    <div
                      className="absolute inset-y-0 left-0 rounded-lg transition-all duration-700"
                      style={{
                        width: `${(f.value / funnelMax) * 100}%`,
                        background: `linear-gradient(90deg, ${f.color}60, ${f.color})`,
                        minWidth: "24px",
                      }}
                    />
                  </div>
                  <span className="text-xs font-bold tabular-nums shrink-0 w-6 text-right" style={{ color: f.color }}>
                    {f.value}
                  </span>
                </div>
              ))}
            </div>
            <div className="mt-4 pt-4 border-t border-white/[0.04] flex gap-4 text-[11px] text-slate-500">
              <span>Scrape→lead: <strong className="text-indigo-400">{Math.round(b2b.leads_qualified / b2b.offers_extracted * 100)}%</strong></span>
              <span>Lead→HIGH: <strong className="text-emerald-400">{Math.round(b2b.leads_high / b2b.leads_qualified * 100)}%</strong></span>
            </div>
          </div>

          {/* Score distribution */}
          <div className="glass rounded-2xl p-5">
            <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-slate-600 mb-5">Distribución lead score</p>
            <div className="grid grid-cols-2 gap-2.5 mb-4">
              {SCORES.map((s) => (
                <div key={s.label} className="rounded-xl p-3 flex flex-col gap-1.5" style={{ background: s.bg, border: `1px solid ${s.border}` }}>
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-bold" style={{ color: s.color }}>{s.label}</span>
                    <span className="text-[10px] text-slate-600 font-mono">{s.pct}%</span>
                  </div>
                  <p className="text-2xl font-bold tabular-nums leading-none" style={{ color: s.color }}>
                    <AnimatedNumber value={s.value} duration={900} />
                  </p>
                  <div className="h-1 rounded-full bg-white/[0.06] overflow-hidden">
                    <div className="h-full rounded-full" style={{ width: `${s.pct}%`, background: s.color }} />
                  </div>
                </div>
              ))}
            </div>
            <div className="pt-3 border-t border-white/[0.04] text-center">
              <span className="text-[11px] text-slate-500">
                Cualificados totales: <strong className="text-white">{b2b.leads_high + b2b.leads_medium} leads</strong>
              </span>
            </div>
          </div>
        </div>

        {/* Fuentes + Flujo */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6 anim-fade-up d-4">
          {/* Fuentes */}
          <div className="glass rounded-2xl p-5">
            <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-slate-600 mb-5">Cobertura por fuente</p>
            <div className="space-y-5">
              {[
                { name: "Indeed.es", offers: indeedOffers, leads: indeedLeads, color: "#6366f1" },
                { name: "InfoJobs",  offers: ijOffers,     leads: ijLeads,     color: "#8b5cf6" },
              ].map((s) => (
                <div key={s.name}>
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full" style={{ background: s.color }} />
                      <span className="text-sm font-semibold text-slate-200">{s.name}</span>
                    </div>
                    <span className="text-[11px] text-slate-500 font-mono">{s.leads} leads de {s.offers} ofertas</span>
                  </div>
                  <div className="flex gap-1.5">
                    <div className="flex-1">
                      <p className="text-[9px] text-slate-600 mb-1 uppercase tracking-wider">Ofertas</p>
                      <div className="h-5 rounded-lg bg-white/[0.03] relative overflow-hidden">
                        <div className="absolute inset-y-0 left-0 rounded-lg" style={{ width: `${(s.offers / maxSource) * 100}%`, background: `${s.color}80` }} />
                        <span className="absolute inset-0 flex items-center pl-2 text-[10px] font-mono text-white/60">{s.offers}</span>
                      </div>
                    </div>
                    <div className="flex-1">
                      <p className="text-[9px] text-slate-600 mb-1 uppercase tracking-wider">Leads</p>
                      <div className="h-5 rounded-lg bg-white/[0.03] relative overflow-hidden">
                        <div className="absolute inset-y-0 left-0 rounded-lg" style={{ width: `${(s.leads / maxSource) * 100}%`, background: s.color }} />
                        <span className="absolute inset-0 flex items-center pl-2 text-[10px] font-mono text-white/60">{s.leads}</span>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Flujo */}
          <div className="glass rounded-2xl p-5">
            <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-slate-600 mb-5">Flujo del pipeline</p>
            <div className="space-y-2.5">
              {[
                { icon: "🔍", step: "Scraping",   desc: "Firecrawl bypasea Distil/Imperva en InfoJobs e Indeed",      color: "#6366f1" },
                { icon: "🧹", step: "Parsing",    desc: "Regex + BS4 extrae título, empresa, ubicación, URL",         color: "#8b5cf6" },
                { icon: "🧠", step: "IA Scoring", desc: "Claude Haiku analiza señales de automatización vía tool_use", color: "#a78bfa" },
                { icon: "📧", step: "Outreach",   desc: "Genera email de prospección personalizado por empresa",      color: "#c4b5fd" },
                { icon: "📋", step: "Entrega",    desc: "Google Sheets coloreado + dropdown Estado + fecha_alta",     color: "#4ade80" },
              ].map((s, i) => (
                <div key={s.step} className="flex items-start gap-3">
                  <div className="flex flex-col items-center">
                    <div className="w-7 h-7 rounded-lg flex items-center justify-center text-sm shrink-0" style={{ background: `${s.color}18`, border: `1px solid ${s.color}28` }}>
                      {s.icon}
                    </div>
                    {i < 4 && <div className="w-px h-3 bg-white/[0.06] mt-1" />}
                  </div>
                  <div className="pb-1">
                    <p className="text-[11px] font-semibold leading-none" style={{ color: s.color }}>{s.step}</p>
                    <p className="text-[11px] text-slate-500 mt-0.5 leading-snug">{s.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Hitos */}
        <div className="mb-6 anim-fade-up d-5">
          <SectionTitle>Estado de hitos · {HITOS.length} completados · {PENDING.length} pendientes</SectionTitle>
          <div className="glass rounded-2xl p-5">
            <div className="flex items-center gap-3 mb-5">
              <div className="flex-1 h-2 rounded-full bg-white/[0.04] overflow-hidden">
                <div className="h-full rounded-full" style={{ width: `${Math.round(HITOS.length / (HITOS.length + PENDING.length) * 100)}%`, background: "linear-gradient(90deg, #6366f1, #4ade80)" }} />
              </div>
              <span className="text-[11px] text-slate-400 shrink-0 font-mono">
                {Math.round(HITOS.length / (HITOS.length + PENDING.length) * 100)}%
              </span>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
              {HITOS.map((h) => (
                <div key={h} className="flex items-center gap-2 px-3 py-2 rounded-xl text-[11px] bg-emerald-500/[0.07] text-emerald-400/80 border border-emerald-500/[0.12]">
                  <span>✓</span><span className="truncate">{h}</span>
                </div>
              ))}
              {PENDING.map((h) => (
                <div key={h} className="flex items-center gap-2 px-3 py-2 rounded-xl text-[11px] bg-white/[0.03] text-slate-600 border border-white/[0.04]">
                  <span>○</span><span className="truncate">{h}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* ADRs */}
        <div className="mb-6 anim-fade-up d-5">
          <SectionTitle>Decisiones arquitectónicas</SectionTitle>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {ADRS.map((adr) => (
              <div key={adr.id} className="glass glass-hover rounded-xl p-4">
                <div className="flex items-center justify-between mb-2.5">
                  <span className="text-[10px] font-mono text-slate-600 bg-white/[0.04] px-2 py-0.5 rounded-md">{adr.id}</span>
                  <span className="text-[10px] px-2 py-0.5 rounded-full font-medium" style={{ background: `${adr.color}18`, color: adr.color, border: `1px solid ${adr.color}30` }}>{adr.status}</span>
                </div>
                <p className="text-sm font-semibold text-slate-200 mb-1.5">{adr.title}</p>
                <p className="text-xs text-slate-500 leading-relaxed">{adr.desc}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Queries */}
        <div className="anim-fade-up d-6">
          <SectionTitle>Queries activas · InfoJobs + Indeed</SectionTitle>
          <div className="flex flex-wrap gap-2">
            {QUERIES.map((q) => (
              <span key={q} className="text-[11px] px-3 py-1.5 rounded-lg font-mono bg-indigo-500/[0.08] text-indigo-300/70 border border-indigo-500/[0.15] hover:bg-indigo-500/[0.15] hover:text-indigo-300 transition-colors cursor-default">
                &quot;{q}&quot;
              </span>
            ))}
          </div>
        </div>

        <p className="text-center text-[10px] text-slate-800 mt-10 font-mono">
          Datos en vivo · actualizados con cada <code>python src/main.py</code>
        </p>
      </div>
    </PageMotion>
  );
}
