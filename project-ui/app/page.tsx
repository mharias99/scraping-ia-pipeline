import { FunnelChart }       from "@/components/charts/FunnelChart";
import { DonutChart }        from "@/components/charts/DonutChart";
import { SourcesBarChart }   from "@/components/charts/SourcesBarChart";
import { TimelineBreakdown } from "@/components/charts/TimelineBreakdown";
import { MetricsBarChart }   from "@/components/charts/MetricsBarChart";
import React from "react";

function Card({ title, children, className = "" }: {
  title: string; children: React.ReactNode; className?: string;
}) {
  return (
    <div className={`bg-zinc-900 border border-zinc-800 rounded-xl p-5 ${className}`}>
      <h2 className="text-xs font-semibold text-zinc-400 uppercase tracking-widest mb-4">{title}</h2>
      {children}
    </div>
  );
}

function KPI({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="bg-zinc-800/60 rounded-lg px-4 py-3 flex flex-col gap-0.5">
      <span className="text-2xl font-bold text-zinc-100 tabular-nums">{value}</span>
      <span className="text-xs text-zinc-400">{label}</span>
      {sub && <span className="text-[10px] text-zinc-600">{sub}</span>}
    </div>
  );
}

export default function Dashboard() {
  return (
    <main className="min-h-screen bg-zinc-950 text-zinc-100 p-6 md:p-10">
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-2xl">🎯</span>
          <h1 className="text-2xl font-bold tracking-tight">Lead Intelligence · Project Dashboard</h1>
          <span className="ml-auto text-xs bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 px-2 py-0.5 rounded-full">
            🟢 Operativo
          </span>
        </div>
        <p className="text-sm text-zinc-500">
          Pipeline B2B: Firecrawl → Claude Haiku → Google Sheets · 2026-05-29
        </p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <KPI label="Ofertas scrapeadas" value="50"  sub="InfoJobs + Indeed · Firecrawl" />
        <KPI label="Leads cualificados" value="31"  sub="62% del total" />
        <KPI label="Leads HIGH"         value="11"  sub="22% · automatización directa" />
        <KPI label="Tiempo pipeline"    value="98s" sub="~$0.005 por ejecución" />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
        <Card title="Embudo de captación de leads">
          <FunnelChart />
        </Card>
        <Card title="Distribución lead score">
          <DonutChart />
          <div className="flex flex-wrap gap-3 mt-4 justify-center">
            {[
              { label: "HIGH",    color: "bg-emerald-400", n: 11 },
              { label: "MEDIUM",  color: "bg-yellow-400",  n: 13 },
              { label: "LOW",     color: "bg-orange-400",  n: 7  },
              { label: "DISCARD", color: "bg-zinc-500",    n: 19 },
            ].map((s) => (
              <div key={s.label} className="flex items-center gap-1.5 text-xs text-zinc-400">
                <span className={`w-2.5 h-2.5 rounded-full ${s.color}`} />
                {s.label} ({s.n})
              </div>
            ))}
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
        <Card title="Cobertura por fuente (ofertas extraídas)">
          <SourcesBarChart />
        </Card>
        <Card title="Métricas clave de sesión">
          <MetricsBarChart />
        </Card>
      </div>

      <Card title="Estado de hitos · 16 completados · 2 en curso · 5 pendientes" className="mb-4">
        <TimelineBreakdown />
        <div className="flex gap-6 mt-3 text-xs text-zinc-400">
          <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-sm bg-emerald-400 inline-block" />Completado (16)</span>
          <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-sm bg-amber-400 inline-block" />En curso (2)</span>
          <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-sm bg-zinc-500 inline-block" />Pendiente (5)</span>
        </div>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[
          { id: "ADR-001", title: "Google Sheets", status: "Activa", color: "emerald",
            desc: "Service Account JSON · gspread · zero-friction para PYMEs · free tier" },
          { id: "ADR-002", title: "Apify (volumen masivo)", status: "Pendiente", color: "amber",
            desc: "Para >500 ofertas/semana · actores mantenidos · proxies rotativos incluidos" },
          { id: "ADR-003", title: "Firecrawl", status: "Activa", color: "emerald",
            desc: "Bypasea Distil/Imperva · 50 ofertas en 17s · 500 créditos/mes free tier" },
        ].map((adr) => (
          <div key={adr.id} className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-mono text-zinc-500">{adr.id}</span>
              <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${
                adr.color === "emerald"
                  ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                  : "bg-amber-500/20 text-amber-400 border border-amber-500/30"
              }`}>
                {adr.status}
              </span>
            </div>
            <p className="text-sm font-semibold text-zinc-200 mb-1">{adr.title}</p>
            <p className="text-xs text-zinc-500 leading-relaxed">{adr.desc}</p>
          </div>
        ))}
      </div>

      <p className="text-center text-xs text-zinc-700 mt-8">
        Powered by Rosen Charts · D3 · Next.js · Tailwind CSS
      </p>
    </main>
  );
}
