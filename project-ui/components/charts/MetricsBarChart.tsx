import React, { CSSProperties } from "react";
import { scaleBand, scaleLinear, max } from "d3";

const data = [
  { key: "Tiempo (s)",     value: 98  },
  { key: "Leads HIGH",     value: 11  },
  { key: "Leads MEDIUM",   value: 13  },
  { key: "Ofertas",        value: 50  },
  { key: "Tests ✓",        value: 39  },
];

export function MetricsBarChart() {
  const xScale = scaleBand()
    .domain(data.map((d) => d.key))
    .range([0, 100])
    .padding(0.25);

  const yScale = scaleLinear()
    .domain([0, max(data.map((d) => d.value)) ?? 0])
    .range([100, 0]);

  return (
    <div
      className="relative w-full h-44"
      style={
        {
          "--marginTop": "8px",
          "--marginRight": "8px",
          "--marginBottom": "28px",
          "--marginLeft": "8px",
        } as CSSProperties
      }
    >
      <div className="absolute inset-0 h-[calc(100%-36px)] w-full translate-y-[8px] overflow-visible">
        <svg className="w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="none">
          {yScale.ticks(4).map((v, i) => (
            <g key={i} transform={`translate(0,${yScale(v)})`} className="text-zinc-700">
              <line x1={0} x2={100} stroke="currentColor" strokeDasharray="4,4" strokeWidth={0.5} vectorEffect="non-scaling-stroke" />
            </g>
          ))}
          {data.map((d, i) => {
            const x = xScale(d.key) ?? 0;
            const w = xScale.bandwidth();
            const y = yScale(d.value);
            return (
              <rect
                key={i}
                x={`${x}%`}
                y={`${y}%`}
                width={`${w}%`}
                height={`${100 - y}%`}
                rx={2}
                fill={i % 2 === 0 ? "#7c3aed" : "#6366f1"}
                fillOpacity={0.85}
              />
            );
          })}
        </svg>
        {data.map((d, i) => (
          <div
            key={i}
            style={{ left: `${(xScale(d.key) ?? 0) + xScale.bandwidth() / 2}%`, top: "100%" }}
            className="absolute text-[10px] text-zinc-400 -translate-x-1/2 tabular-nums text-center w-16 leading-tight"
          >
            {d.key}
          </div>
        ))}
      </div>
    </div>
  );
}
