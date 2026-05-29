import React, { CSSProperties } from "react";
import { scaleBand, scaleLinear, max } from "d3";

const data = [
  { key: "Indeed.es",  value: 38, color: "#6366f1" },
  { key: "InfoJobs",   value: 12, color: "#8b5cf6" },
];

export function SourcesBarChart() {
  const yScale = scaleBand()
    .domain(data.map((d) => d.key))
    .range([0, 100])
    .padding(0.3);

  const xScale = scaleLinear()
    .domain([0, max(data.map((d) => d.value)) ?? 0])
    .range([0, 100]);

  return (
    <div
      className="relative w-full h-28"
      style={{ "--marginLeft": "80px", "--marginBottom": "20px" } as CSSProperties}
    >
      <div
        className="absolute inset-0 h-[calc(100%-20px)] w-[calc(100%-80px)] translate-x-[80px] overflow-visible"
      >
        {data.map((d, i) => (
          <div
            key={i}
            style={{
              top: `${yScale(d.key)}%`,
              width: `${xScale(d.value)}%`,
              height: `${yScale.bandwidth()}%`,
              borderRadius: "0 6px 6px 0",
              backgroundColor: d.color,
              position: "absolute",
              left: 0,
            }}
          />
        ))}
        <svg className="h-full w-full" viewBox="0 0 100 100" preserveAspectRatio="none">
          {xScale.ticks(5).map((v, i) => (
            <g key={i} transform={`translate(${xScale(v)},0)`} className="text-zinc-700">
              <line y1={0} y2={100} stroke="currentColor" strokeDasharray="4,4" strokeWidth={0.5} vectorEffect="non-scaling-stroke" />
            </g>
          ))}
        </svg>
        {xScale.ticks(5).map((v, i) => (
          <div key={i} style={{ left: `${xScale(v)}%`, top: "100%" }} className="absolute text-xs -translate-x-1/2 text-zinc-500 tabular-nums">
            {v}
          </div>
        ))}
      </div>
      <div className="absolute h-[calc(100%-20px)] w-[80px] overflow-visible">
        {data.map((d, i) => (
          <span key={i} style={{ top: `${yScale(d.key)! + yScale.bandwidth() / 2}%` }}
            className="absolute text-xs text-zinc-400 -translate-y-1/2 w-full text-right pr-2">
            {d.key}
          </span>
        ))}
      </div>
    </div>
  );
}
