import React, { CSSProperties } from "react";

// Lead pipeline funnel — Rosen Charts style
const data = [
  { key: "Páginas scrapeadas", value: 10, color: "from-sky-400 to-sky-500 dark:from-sky-500 dark:to-sky-700" },
  { key: "Ofertas extraídas", value: 50, color: "from-indigo-400 to-indigo-500 dark:from-indigo-500 dark:to-indigo-700" },
  { key: "Leads cualificados", value: 31, color: "from-violet-400 to-violet-500 dark:from-violet-500 dark:to-violet-700" },
  { key: "Leads HIGH", value: 11, color: "from-emerald-400 to-emerald-500 dark:from-emerald-500 dark:to-emerald-700" },
];

export function FunnelChart() {
  const gap = 0.3;
  const maxValue = Math.max(...data.map((d) => d.value));
  const barHeight = 58;
  let cumulativeHeight = 0;

  return (
    <div
      className="relative mt-4"
      style={{ "--height": `${barHeight * data.length + gap * (data.length - 1) * 10}px` } as CSSProperties}
    >
      <div className="relative" style={{ height: `${barHeight * data.length + gap * (data.length - 1) * 10}px` }}>
        {data.map((d, i) => {
          const barWidth = (d.value / maxValue) * 100;
          const yPos = cumulativeHeight;
          cumulativeHeight += barHeight + 8;
          return (
            <div
              key={i}
              className={`absolute bg-gradient-to-b ${d.color} rounded-md flex flex-col items-center justify-center gap-0.5`}
              style={{
                top: `${yPos}px`,
                left: `${(100 - barWidth) / 2}%`,
                width: `${barWidth}%`,
                height: `${barHeight}px`,
              }}
            >
              <span className="text-white text-sm font-semibold">{d.key}</span>
              <span className="text-white/80 text-xs font-mono font-bold">{d.value}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
