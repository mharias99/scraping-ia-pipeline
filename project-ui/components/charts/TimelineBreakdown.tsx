import React, { CSSProperties } from "react";

const data = [
  { key: "Completado", value: 16, color: "from-emerald-400 to-emerald-500" },
  { key: "En curso",   value: 2,  color: "from-amber-400 to-amber-500" },
  { key: "Pendiente",  value: 5,  color: "from-zinc-500 to-zinc-600" },
];

const cornerRadius = 6;
const barHeight = 48;

export function TimelineBreakdown() {
  const total = data.reduce((s, d) => s + d.value, 0);
  let cum = 0;

  return (
    <div className="relative" style={{ height: `${barHeight}px` }}>
      {data.map((d, i) => {
        const w = (d.value / total) * 100;
        const x = cum;
        cum += w;
        const isFirst = i === 0;
        const isLast  = i === data.length - 1;
        return (
          <div
            key={i}
            className={`absolute bg-gradient-to-b ${d.color} flex items-center justify-center gap-1`}
            style={{
              left: `${x}%`,
              width: `${w}%`,
              height: `${barHeight}px`,
              borderRadius: isFirst
                ? `${cornerRadius}px 0 0 ${cornerRadius}px`
                : isLast
                ? `0 ${cornerRadius}px ${cornerRadius}px 0`
                : "0",
            }}
          >
            <span className="text-white text-xs font-semibold">{d.key}</span>
            <span className="text-white/80 text-xs font-mono">({d.value})</span>
          </div>
        );
      })}
    </div>
  );
}
