import { PageMotion }                 from "@/components/PageMotion";
import { AnimatedNumber }             from "@/components/AnimatedNumber";
import { loadStats, formatUpdatedAt } from "@/lib/stats";
import Link                           from "next/link";

const SECTORS = [
  { name: "Clínicas estéticas",   total: 25, high: 11, medium: 9,  score: 3.8, icon: "💉" },
  { name: "Dentistas",             total: 25, high: 9,  medium: 8,  score: 4.1, icon: "🦷" },
  { name: "Peluquerías y salones", total: 25, high: 8,  medium: 7,  score: 3.6, icon: "✂️" },
  { name: "Talleres mecánicos",    total: 25, high: 7,  medium: 10, score: 3.2, icon: "🔧" },
  { name: "Academias de idiomas",  total: 25, high: 7,  medium: 8,  score: 3.9, icon: "🗣️" },
];

const WEAKNESSES = [
  { label: "Sin web propia",             pct: 52, color: "#ef4444" },
  { label: "Sin HTTPS / web insegura",   pct: 68, color: "#f97316" },
  { label: "Sin reservas/citas online",  pct: 71, color: "#f59e0b" },
  { label: "Sin pixel Meta/GA",          pct: 84, color: "#eab308" },
  { label: "Puntuación Maps <4.0",       pct: 34, color: "#6366f1" },
  { label: "Menos de 50 reseñas",        pct: 61, color: "#8b5cf6" },
];

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-3 mb-4">
      <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-slate-600">{children}</p>
      <div className="flex-1 h-px bg-white/[0.04]" />
    </div>
  );
}

export default function DigitalPage() {
  const stats   = loadStats();
  const digital = stats.digital_audit;
  const updatedLabel = formatUpdatedAt(stats.updated_at);

  const KPIS = [
    { label: "Sectores analizados",      value: 5,                          suffix: "",  icon: "🏢", hint: "Madrid centro" },
    { label: "Negocios auditados",       value: digital.businesses_audited, suffix: "",  icon: "🔍", hint: "Google Maps top 25" },
    { label: "Clientes HIGH",            value: digital.clients_high,       suffix: "",  icon: "⚡", hint: "Necesitan todo" },
    { label: "Clientes MEDIUM",          value: digital.clients_medium,     suffix: "",  icon: "📊", hint: "Mejoras puntuales" },
    { label: "Sin web óptima",           value: digital.pct_no_web,         suffix: "%", icon: "⚠️", hint: "Sin HTTPS o sin web" },
    { label: "Sin reservas online",      value: digital.pct_no_booking,     suffix: "%", icon: "📅", hint: "Pérdida conversión" },
  ];

  const SCORES = [
    { label: "HIGH",   count: digital.clients_high,   color: "#06b6d4", desc: "Necesita web, SEO, reservas", pct: Math.round(digital.clients_high  / Math.max(digital.businesses_audited, 1) * 100) },
    { label: "MEDIUM", count: digital.clients_medium, color: "#3b82f6", desc: "Necesita mejoras puntuales",   pct: Math.round(digital.clients_medium / Math.max(digital.businesses_audited, 1) * 100) },
    { label: "LOW",
      count: Math.max(digital.businesses_audited - digital.clients_high - digital.clients_medium, 0),
      color: "#6b7280", desc: "Presencia básica adecuada",
      pct: Math.max(100 - Math.round(digital.clients_high / Math.max(digital.businesses_audited, 1) * 100) - Math.round(digital.clients_medium / Math.max(digital.businesses_audited, 1) * 100), 0) },
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
            <div className="w-9 h-9 rounded-xl flex items-center justify-center text-lg" style={{ background: "linear-gradient(135deg, #06b6d430, #06b6d415)", border: "1px solid #06b6d430" }}>📡</div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-white">Auditoría Digital</h1>
              <p className="text-xs text-slate-500 mt-0.5">Google Maps · Firecrawl + Claude Haiku · Madrid · 5 sectores</p>
            </div>
            <div className="ml-auto text-right">
              <span className="text-[11px] px-2.5 py-1 rounded-full bg-cyan-500/15 text-cyan-300 border border-cyan-500/25 font-medium">Demo pipeline</span>
              <p className="text-[10px] text-slate-600 font-mono mt-1">{updatedLabel}</p>
            </div>
          </div>
          <div className="mt-5 h-px bg-gradient-to-r from-cyan-500/30 via-white/[0.06] to-transparent" />
        </div>

        {/* KPIs */}
        <div className="mb-8 anim-fade-up d-1">
          <SectionTitle>Métricas · sesión demo · Madrid</SectionTitle>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
            {KPIS.map((k, i) => (
              <div key={k.label} className="glass glass-hover rounded-2xl p-4 flex flex-col gap-2 hover:glow-cyan transition-all duration-300" style={{ animationDelay: `${i * 50}ms` }}>
                <div className="flex items-center justify-between">
                  <span className="w-7 h-7 rounded-lg bg-cyan-500/15 flex items-center justify-center text-sm">{k.icon}</span>
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

        {/* Sectores + Debilidades */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6 anim-fade-up d-3">
          <div className="glass rounded-2xl p-5">
            <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-slate-600 mb-5">Clientes HIGH por sector · Madrid</p>
            <div className="space-y-4">
              {SECTORS.map((s) => {
                const hp = (s.high  / s.total) * 100;
                const mp = (s.medium / s.total) * 100;
                return (
                  <div key={s.name}>
                    <div className="flex items-center justify-between mb-1.5">
                      <div className="flex items-center gap-2">
                        <span className="text-sm">{s.icon}</span>
                        <span className="text-[12px] text-slate-300 font-medium">{s.name}</span>
                      </div>
                      <div className="flex items-center gap-2 text-[10px]">
                        <span className="text-cyan-400 font-bold">{s.high} HIGH</span>
                        <span className="text-slate-600">·</span>
                        <span className="text-slate-500">⭐ {s.score}</span>
                      </div>
                    </div>
                    <div className="flex h-3 rounded-lg overflow-hidden bg-white/[0.03]">
                      <div className="h-full" style={{ width: `${hp}%`, background: "#06b6d4" }} />
                      <div className="h-full" style={{ width: `${mp}%`, background: "#3b82f6" }} />
                    </div>
                    <div className="flex items-center gap-3 mt-1 text-[9px] text-slate-600">
                      <span><span className="text-cyan-400">■</span> HIGH ({s.high})</span>
                      <span><span className="text-blue-400">■</span> MEDIUM ({s.medium})</span>
                      <span className="ml-auto">{s.total} auditados</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="glass rounded-2xl p-5">
            <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-slate-600 mb-5">Debilidades más frecuentes</p>
            <div className="space-y-3">
              {WEAKNESSES.map((w) => (
                <div key={w.label} className="flex items-center gap-3">
                  <span className="text-[11px] text-slate-400 w-40 shrink-0">{w.label}</span>
                  <div className="flex-1 h-5 rounded-lg bg-white/[0.03] relative overflow-hidden">
                    <div className="absolute inset-y-0 left-0 rounded-lg" style={{ width: `${w.pct}%`, background: `linear-gradient(90deg, ${w.color}80, ${w.color})` }} />
                  </div>
                  <span className="text-xs font-bold tabular-nums shrink-0 w-8 text-right" style={{ color: w.color }}>{w.pct}%</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Score distribution */}
        <div className="mb-6 anim-fade-up d-4">
          <SectionTitle>Distribución de prioridad</SectionTitle>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {SCORES.map((s) => (
              <div key={s.label} className="glass glass-hover rounded-2xl p-5">
                <div className="flex items-center justify-between mb-4">
                  <span className="text-xs font-bold px-2.5 py-1 rounded-lg" style={{ background: `${s.color}15`, color: s.color, border: `1px solid ${s.color}25` }}>{s.label}</span>
                  <span className="text-[11px] text-slate-600 font-mono">{s.pct}%</span>
                </div>
                <p className="text-4xl font-bold text-white tabular-nums mb-1.5">
                  <AnimatedNumber value={s.count} duration={900} />
                </p>
                <p className="text-xs text-slate-500">{s.desc}</p>
                <div className="mt-3 h-1 rounded-full bg-white/[0.04] overflow-hidden">
                  <div className="h-full rounded-full" style={{ width: `${s.pct}%`, background: s.color }} />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Script ejemplo */}
        <div className="mb-6 anim-fade-up d-5">
          <SectionTitle>Script de captación generado por IA</SectionTitle>
          <div className="glass rounded-2xl p-5" style={{ borderLeft: "3px solid rgba(6,182,212,0.4)" }}>
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-lg flex items-center justify-center text-sm shrink-0 mt-0.5" style={{ background: "rgba(6,182,212,0.12)", border: "1px solid rgba(6,182,212,0.2)" }}>🤖</div>
              <div>
                <p className="text-xs font-semibold text-cyan-400 mb-1">Claude Haiku · script generado para: Centro Dental López (HIGH)</p>
                <p className="text-sm text-slate-300 leading-relaxed italic">
                  &quot;Buenos días, soy [nombre] de [agencia]. He visto su consulta en Google Maps y noto que no tienen sistema de citas online. En su sector, las clínicas con reservas web aumentan un 40% la conversión de nuevos pacientes. ¿Le gustaría que le mostremos cómo podría implementarlo en menos de una semana?&quot;
                </p>
                <div className="flex gap-2 mt-3">
                  {["Sin web de citas", "4.2⭐ Maps", "68 reseñas", "Madrid Centro"].map((t) => (
                    <span key={t} className="text-[10px] px-2 py-0.5 rounded-md font-mono" style={{ background: "rgba(6,182,212,0.08)", color: "#22d3ee", border: "1px solid rgba(6,182,212,0.15)" }}>{t}</span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Flujo */}
        <div className="anim-fade-up d-6">
          <SectionTitle>Flujo del pipeline</SectionTitle>
          <div className="glass rounded-2xl p-5">
            <div className="flex flex-col md:flex-row items-start md:items-center">
              {[
                { icon: "🗺️", step: "1. Google Maps",  desc: "Top 25 negocios por sector + rating" },
                { icon: "🌐", step: "2. Web Inspector", desc: "Firecrawl analiza web, HTTPS, pixel, booking" },
                { icon: "🧠", step: "3. Scoring IA",    desc: "Claude Haiku: digital_score + call_script" },
                { icon: "📋", step: "4. Entrega",       desc: "Sheet con leads HIGH primero + guion de llamada" },
              ].map((s, i) => (
                <div key={s.step} className="flex-1 flex items-start gap-3 py-3 md:py-0 md:px-4">
                  {i > 0 && (
                    <div className="hidden md:flex items-center self-center text-slate-700 mr-[-8px] ml-[-20px]">
                      <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
                      </svg>
                    </div>
                  )}
                  <div className="w-9 h-9 rounded-xl flex items-center justify-center text-base shrink-0" style={{ background: "rgba(6,182,212,0.12)", border: "1px solid rgba(6,182,212,0.2)" }}>{s.icon}</div>
                  <div>
                    <p className="text-xs font-semibold text-cyan-400/80">{s.step}</p>
                    <p className="text-[11px] text-slate-500 mt-0.5 leading-snug">{s.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <p className="text-center text-[10px] text-slate-800 mt-10 font-mono">
          Datos en vivo · actualizados con cada <code>python src/main.py --config configs/demo_digital.yaml</code>
        </p>
      </div>
    </PageMotion>
  );
}
