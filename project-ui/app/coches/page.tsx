import { PageMotion }                 from "@/components/PageMotion";
import { AnimatedNumber }             from "@/components/AnimatedNumber";
import { loadStats, formatUpdatedAt } from "@/lib/stats";
import Link                           from "next/link";

const MODELS = [
  { name: "Seat Ibiza",        total: 50, high: 9,  delta: 2400, color: "#6366f1" },
  { name: "Volkswagen Golf",   total: 50, high: 11, delta: 4100, color: "#8b5cf6" },
  { name: "Cupra León",        total: 50, high: 7,  delta: 5200, color: "#a78bfa" },
  { name: "Toyota Yaris Híb.", total: 50, high: 8,  delta: 2800, color: "#f59e0b" },
  { name: "Renault Clio",      total: 50, high: 6,  delta: 1900, color: "#f97316" },
  { name: "Peugeot 208",       total: 50, high: 5,  delta: 2100, color: "#fb923c" },
  { name: "Hyundai Tucson",    total: 50, high: 6,  delta: 3600, color: "#fbbf24" },
];

const maxDelta = Math.max(...MODELS.map((m) => m.delta));
const maxHigh  = Math.max(...MODELS.map((m) => m.high));

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-3 mb-4">
      <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-slate-600">{children}</p>
      <div className="flex-1 h-px bg-white/[0.04]" />
    </div>
  );
}

export default function CochesPage() {
  const stats  = loadStats();
  const cars   = stats.car_arbitrage;
  const updatedLabel = formatUpdatedAt(stats.updated_at);

  const TIERS = [
    { label: "HIGH",    desc: "≥15% bajo mercado",  count: cars.opportunities_high,   color: "#f59e0b",
      pct: Math.round(cars.opportunities_high   / Math.max(cars.ads_analyzed, 1) * 100) },
    { label: "MEDIUM",  desc: "8–14% bajo mercado", count: cars.opportunities_medium, color: "#f97316",
      pct: Math.round(cars.opportunities_medium / Math.max(cars.ads_analyzed, 1) * 100) },
    { label: "NORMAL",  desc: "Precio de mercado",
      count: Math.max(cars.ads_analyzed - cars.opportunities_high - cars.opportunities_medium - Math.round(cars.ads_analyzed * 0.12), 0),
      color: "#6b7280", pct: 48 },
    { label: "SOBREV.", desc: "Por encima mercado",
      count: Math.round(cars.ads_analyzed * 0.12), color: "#ef4444", pct: 12 },
  ];

  const KPIS = [
    { label: "Modelos monitorizados",  value: 7,                            suffix: "",  icon: "🚙", hint: "Milanuncios particulares" },
    { label: "Anuncios analizados",    value: cars.ads_analyzed,            suffix: "",  icon: "🔍", hint: "Apify + Claude Haiku" },
    { label: "Oportunidades HIGH",     value: cars.opportunities_high,      suffix: "",  icon: "⚡", hint: "≥15% bajo precio mercado" },
    { label: "Oportunidades MEDIUM",   value: cars.opportunities_medium,    suffix: "",  icon: "📊", hint: "8–14% bajo precio mercado" },
    { label: "Delta precio medio",     value: cars.avg_delta_eur,           suffix: "€", icon: "💰", hint: "Por oportunidad HIGH" },
    { label: "ROI estimado / unidad",  value: Math.round(cars.avg_delta_eur * 0.75), suffix: "€", icon: "📈", hint: "Neto tras gastos" },
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
            <div className="w-9 h-9 rounded-xl flex items-center justify-center text-lg" style={{ background: "linear-gradient(135deg, #f59e0b30, #f59e0b15)", border: "1px solid #f59e0b30" }}>🚗</div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-white">Arbitraje de Vehículos</h1>
              <p className="text-xs text-slate-500 mt-0.5">Milanuncios · Apify + Claude Haiku · Google Sheets</p>
            </div>
            <div className="ml-auto text-right">
              <span className="text-[11px] px-2.5 py-1 rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/25 font-medium">Demo pipeline</span>
              <p className="text-[10px] text-slate-600 font-mono mt-1">{updatedLabel}</p>
            </div>
          </div>
          <div className="mt-5 h-px bg-gradient-to-r from-amber-500/30 via-white/[0.06] to-transparent" />
        </div>

        {/* KPIs */}
        <div className="mb-8 anim-fade-up d-1">
          <SectionTitle>Métricas · sesión demo</SectionTitle>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
            {KPIS.map((k, i) => (
              <div key={k.label} className="glass glass-hover rounded-2xl p-4 flex flex-col gap-2 hover:glow-amber transition-all duration-300" style={{ animationDelay: `${i * 50}ms` }}>
                <div className="flex items-center justify-between">
                  <span className="w-7 h-7 rounded-lg bg-amber-500/15 flex items-center justify-center text-sm">{k.icon}</span>
                  <span className="text-[9px] text-slate-700 font-mono truncate max-w-[80px] text-right">{k.hint}</span>
                </div>
                <div>
                  <p className="text-2xl font-bold text-white tabular-nums leading-none">
                    <AnimatedNumber value={k.value} suffix={k.suffix} duration={900} />
                  </p>
                  <p className="text-[10px] text-slate-500 mt-1 leading-tight">{k.label}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Barras por modelo */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6 anim-fade-up d-3">
          <div className="glass rounded-2xl p-5">
            <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-slate-600 mb-5">Oportunidades HIGH por modelo</p>
            <div className="space-y-3">
              {MODELS.map((m) => (
                <div key={m.name} className="flex items-center gap-3">
                  <span className="text-[11px] text-slate-400 w-32 shrink-0 truncate">{m.name}</span>
                  <div className="flex-1 h-5 rounded-lg bg-white/[0.03] relative overflow-hidden">
                    <div className="absolute inset-y-0 left-0 rounded-lg" style={{ width: `${(m.high / maxHigh) * 100}%`, background: `linear-gradient(90deg, ${m.color}99, ${m.color})` }} />
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className="text-xs font-bold tabular-nums" style={{ color: m.color }}>{m.high}</span>
                    <span className="text-[10px] text-slate-600 font-mono">/{m.total}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="glass rounded-2xl p-5">
            <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-slate-600 mb-5">Delta precio medio HIGH (€)</p>
            <div className="space-y-3">
              {MODELS.map((m) => (
                <div key={m.name} className="flex items-center gap-3">
                  <span className="text-[11px] text-slate-400 w-32 shrink-0 truncate">{m.name}</span>
                  <div className="flex-1 h-5 rounded-lg bg-white/[0.03] relative overflow-hidden">
                    <div className="absolute inset-y-0 left-0 rounded-lg" style={{ width: `${(m.delta / maxDelta) * 100}%`, background: "linear-gradient(90deg, rgba(245,158,11,0.5), #f59e0b)" }} />
                  </div>
                  <span className="text-xs font-bold tabular-nums text-amber-400 shrink-0 w-16 text-right">{m.delta.toLocaleString("es-ES")}€</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Tiers */}
        <div className="mb-6 anim-fade-up d-4">
          <SectionTitle>Distribución de oportunidades</SectionTitle>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {TIERS.map((t) => (
              <div key={t.label} className="glass glass-hover rounded-2xl p-4 text-center">
                <div className="w-10 h-10 rounded-xl mx-auto mb-3 flex items-center justify-center text-base font-bold" style={{ background: `${t.color}20`, color: t.color, border: `1px solid ${t.color}30` }}>
                  {t.pct}%
                </div>
                <p className="text-2xl font-bold text-white tabular-nums mb-0.5">
                  <AnimatedNumber value={t.count} duration={900} />
                </p>
                <p className="text-xs font-semibold mb-1" style={{ color: t.color }}>{t.label}</p>
                <p className="text-[10px] text-slate-600">{t.desc}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Flujo */}
        <div className="anim-fade-up d-5">
          <SectionTitle>Flujo del pipeline</SectionTitle>
          <div className="glass rounded-2xl p-5">
            <div className="flex flex-col md:flex-row items-start md:items-center gap-0 md:gap-0">
              {[
                { icon: "🔍", step: "1. Scraping",   desc: "Apify raspa Milanuncios con proxies rotativos" },
                { icon: "🧠", step: "2. IA pricing",  desc: "Claude Haiku calcula precio de mercado por modelo/año/km" },
                { icon: "📊", step: "3. Scoring",     desc: "Clasifica HIGH/MEDIUM/NORMAL/SOBREVALORADO" },
                { icon: "📋", step: "4. Entrega",     desc: "Google Sheets coloreado + ordenado por oportunidad" },
              ].map((s, i) => (
                <div key={s.step} className="flex-1 flex items-start gap-3 py-3 md:py-0 md:px-4">
                  {i > 0 && (
                    <div className="hidden md:flex items-center self-center text-slate-700 mr-[-8px] ml-[-20px]">
                      <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
                      </svg>
                    </div>
                  )}
                  <div className="w-9 h-9 rounded-xl flex items-center justify-center text-base shrink-0" style={{ background: "rgba(245,158,11,0.12)", border: "1px solid rgba(245,158,11,0.2)" }}>
                    {s.icon}
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-amber-400/80">{s.step}</p>
                    <p className="text-[11px] text-slate-500 mt-0.5 leading-snug">{s.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <p className="text-center text-[10px] text-slate-800 mt-10 font-mono">
          Pipeline Coches · Threshold 15% · Vendedores privados · Apify Milanuncios actor
        </p>
      </div>
    </PageMotion>
  );
}
