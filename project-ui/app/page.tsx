import { PageMotion }                       from "@/components/PageMotion";
import { AnimatedNumber }                   from "@/components/AnimatedNumber";
import { loadStats, formatUpdatedAt }       from "@/lib/stats";
import Link                                 from "next/link";

const STATIC = [
  {
    href: "/b2b",
    icon: "🎯",
    name: "B2B Lead Intelligence",
    tagline: "InfoJobs + Indeed · Firecrawl + Claude Haiku",
    accentColor: "#6366f1",
    gradClass: "from-indigo-600/20 via-violet-600/10 to-transparent",
    borderHover: "hover:border-indigo-500/40",
    glowClass: "glow-indigo",
    badgeClass: "bg-indigo-500/15 text-indigo-300 border border-indigo-500/25",
    badge: "Activo",
    description: "Detecta PYMEs con backoffice manual en InfoJobs e Indeed. Claude Haiku las clasifica como candidatas a automatización.",
    costLabel: "~$0.005/ejecución",
  },
  {
    href: "/coches",
    icon: "🚗",
    name: "Arbitraje de Vehículos",
    tagline: "Milanuncios · Apify + Claude Haiku",
    accentColor: "#f59e0b",
    gradClass: "from-amber-600/20 via-orange-600/10 to-transparent",
    borderHover: "hover:border-amber-500/40",
    glowClass: "glow-amber",
    badgeClass: "bg-amber-500/15 text-amber-300 border border-amber-500/25",
    badge: "Demo",
    description: "Detecta coches de particular ≥15% por debajo de precio de mercado para arbitraje o reventa.",
    costLabel: "~$0.008/ejecución",
  },
  {
    href: "/digital",
    icon: "📡",
    name: "Auditoría Digital",
    tagline: "Google Maps · Firecrawl + Claude Haiku",
    accentColor: "#06b6d4",
    gradClass: "from-cyan-600/20 via-blue-600/10 to-transparent",
    borderHover: "hover:border-cyan-500/40",
    glowClass: "glow-cyan",
    badgeClass: "bg-cyan-500/15 text-cyan-300 border border-cyan-500/25",
    badge: "Demo",
    description: "Audita negocios locales en Google Maps. Detecta quién necesita web, HTTPS, reservas online o mejor reputación.",
    costLabel: "~$0.004/ejecución",
  },
];

export default function CommandCenter() {
  const stats  = loadStats();
  const b2b    = stats.b2b_leads;
  const cars   = stats.car_arbitrage;
  const digital = stats.digital_audit;
  const updatedLabel = formatUpdatedAt(stats.updated_at);

  const kpis = [
    {
      href: "/b2b",
      kpis: [
        { label: "Ofertas scrapeadas", value: b2b.offers_extracted,  suffix: "",  icon: "🔍" },
        { label: "Leads cualificados", value: b2b.leads_qualified,   suffix: "",  icon: "✅" },
        { label: "HIGH prioridad",     value: b2b.leads_high,        suffix: "",  icon: "⚡" },
        { label: "Tiempo pipeline",    value: b2b.pipeline_time_s,   suffix: "s", icon: "⏱" },
      ],
    },
    {
      href: "/coches",
      kpis: [
        { label: "Anuncios analizados",  value: cars.ads_analyzed,          suffix: "",  icon: "🔍" },
        { label: "Oportunidades HIGH",   value: cars.opportunities_high,    suffix: "",  icon: "⚡" },
        { label: "Oportunidades MEDIUM", value: cars.opportunities_medium,  suffix: "",  icon: "📊" },
        { label: "Delta precio medio",   value: cars.avg_delta_eur,         suffix: "€", icon: "💰" },
      ],
    },
    {
      href: "/digital",
      kpis: [
        { label: "Negocios auditados",  value: digital.businesses_audited, suffix: "",  icon: "🔍" },
        { label: "Clientes HIGH",       value: digital.clients_high,       suffix: "",  icon: "⚡" },
        { label: "Clientes MEDIUM",     value: digital.clients_medium,     suffix: "",  icon: "📊" },
        { label: "Sin web óptima",      value: digital.pct_no_web,         suffix: "%", icon: "⚠️" },
      ],
    },
  ];

  const totalLeads = b2b.leads_high + b2b.leads_medium
    + cars.opportunities_high + digital.clients_high;

  const globalKpis = [
    { label: "Pipelines activos",   value: 3,          suffix: "",   icon: "🔄" },
    { label: "Leads HIGH totales",  value: totalLeads, suffix: "",   icon: "⚡" },
    { label: "Coste/ejecución",     value: 0.005,      suffix: "$",  icon: "💲", decimals: 3 },
    { label: "Último pipeline",     value: b2b.pipeline_time_s, suffix: "s", icon: "⏱" },
  ];

  return (
    <PageMotion>
      <div className="px-8 py-8 max-w-6xl mx-auto">

        {/* Header */}
        <div className="mb-10 anim-fade-up d-0">
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <h1 className="text-3xl font-bold tracking-tight text-white">Command Center</h1>
                <span className="text-[11px] px-2.5 py-1 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/25 font-medium">
                  🟢 Operativo
                </span>
              </div>
              <p className="text-slate-400 text-sm max-w-lg">
                Tres pipelines de inteligencia de negocio. Cada uno detecta una oportunidad de mercado diferente.
              </p>
            </div>
            <div className="text-right hidden md:block">
              <p className="text-[11px] text-slate-600 font-mono">Última ejecución</p>
              <p className="text-xs text-slate-400 font-mono mt-0.5">{updatedLabel}</p>
              {stats.last_run_type && (
                <p className="text-[10px] text-slate-700 font-mono mt-0.5">{stats.last_run_type}</p>
              )}
            </div>
          </div>
          <div className="mt-6 h-px bg-gradient-to-r from-indigo-500/30 via-white/[0.06] to-transparent" />
        </div>

        {/* Global KPIs */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-10 anim-fade-up d-1">
          {globalKpis.map((k) => (
            <div key={k.label} className="glass glass-hover rounded-xl px-4 py-3 flex items-center gap-3">
              <span className="text-xl">{k.icon}</span>
              <div>
                <p className="text-xl font-bold text-white tabular-nums leading-none">
                  <AnimatedNumber value={k.value} suffix={k.suffix} decimals={"decimals" in k ? (k as {decimals: number}).decimals : 0} duration={900} />
                </p>
                <p className="text-[11px] text-slate-500 mt-0.5">{k.label}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Section label */}
        <div className="flex items-center gap-3 mb-5 anim-fade-up d-2">
          <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-slate-600">Oportunidades de negocio</p>
          <div className="flex-1 h-px bg-white/[0.04]" />
        </div>

        {/* Opportunity cards */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 mb-12">
          {STATIC.map((opp, i) => {
            const liveKpis = kpis[i].kpis;
            return (
              <Link key={opp.href} href={opp.href} className="block group">
                <div
                  className={`relative overflow-hidden glass glass-hover ${opp.borderHover} ${opp.glowClass}
                               rounded-2xl p-6 h-full cursor-pointer transition-all duration-300
                               anim-fade-up`}
                  style={{ animationDelay: `${(i + 3) * 60}ms` }}
                >
                  {/* Gradient bg */}
                  <div className={`absolute inset-0 bg-gradient-to-br ${opp.gradClass} opacity-60 group-hover:opacity-100 transition-opacity duration-300`} />

                  <div className="relative z-10">
                    {/* Header */}
                    <div className="flex items-start justify-between mb-5">
                      <div className="flex items-center gap-2.5">
                        <div
                          className="w-10 h-10 rounded-xl flex items-center justify-center text-xl shadow-lg"
                          style={{ background: `${opp.accentColor}25`, border: `1px solid ${opp.accentColor}30` }}
                        >
                          {opp.icon}
                        </div>
                        <div>
                          <p className="text-[13px] font-bold text-white leading-tight">{opp.name}</p>
                          <p className="text-[10px] text-slate-500 mt-0.5 leading-tight">{opp.tagline}</p>
                        </div>
                      </div>
                      <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium shrink-0 ${opp.badgeClass}`}>
                        {opp.badge}
                      </span>
                    </div>

                    {/* KPIs */}
                    <div className="grid grid-cols-2 gap-2 mb-5">
                      {liveKpis.map((kpi) => (
                        <div
                          key={kpi.label}
                          className="rounded-xl px-3 py-2.5"
                          style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.05)" }}
                        >
                          <div className="flex items-center gap-1.5 mb-0.5">
                            <span className="text-[11px]">{kpi.icon}</span>
                            <p className="text-[9px] text-slate-500 uppercase tracking-wider leading-none">{kpi.label}</p>
                          </div>
                          <p className="text-lg font-bold tabular-nums leading-none" style={{ color: opp.accentColor }}>
                            <AnimatedNumber value={kpi.value} suffix={kpi.suffix} duration={800 + i * 100} />
                          </p>
                        </div>
                      ))}
                    </div>

                    {/* Description */}
                    <p className="text-[12px] text-slate-400 leading-relaxed mb-5 min-h-[48px]">
                      {opp.description}
                    </p>

                    {/* Footer */}
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] text-slate-600 font-mono">{opp.costLabel}</span>
                      <span
                        className="flex items-center gap-1.5 text-[12px] font-semibold group-hover:gap-2.5 transition-all duration-200"
                        style={{ color: opp.accentColor }}
                      >
                        Ver dashboard
                        <svg className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform duration-200"
                          fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" />
                        </svg>
                      </span>
                    </div>
                  </div>
                </div>
              </Link>
            );
          })}
        </div>

        {/* Tech stack */}
        <div className="anim-fade-up d-6">
          <p className="text-[9px] font-bold uppercase tracking-[0.12em] text-slate-700 mb-3">Stack tecnológico</p>
          <div className="flex flex-wrap gap-2">
            {["Python 3.11", "Firecrawl", "Apify", "Claude Haiku", "Google Sheets", "Playwright", "pandas", "Next.js", "D3"].map((t) => (
              <span
                key={t}
                className="text-[11px] px-2.5 py-1 rounded-lg font-mono text-slate-500
                           border border-white/[0.05] bg-white/[0.02] hover:text-slate-300
                           hover:border-white/[0.1] transition-colors duration-150 cursor-default"
              >
                {t}
              </span>
            ))}
          </div>
        </div>

        <p className="text-center text-[10px] text-slate-800 mt-12 font-mono">
          LeadOS · datos actualizados con cada ejecución del pipeline
        </p>
      </div>
    </PageMotion>
  );
}
