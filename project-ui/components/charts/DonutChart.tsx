"use client";
import { pie, arc, PieArcDatum } from "d3";

type Item = { name: string; value: number; color: string };

const data: Item[] = [
  { name: "HIGH",    value: 11, color: "#4ade80" },
  { name: "MEDIUM",  value: 13, color: "#facc15" },
  { name: "LOW",     value: 7,  color: "#fb923c" },
  { name: "DISCARD", value: 19, color: "#6b7280" },
];

const total = data.reduce((s, d) => s + d.value, 0);

export function DonutChart() {
  const radius = 420;
  const gap = 0.02;
  const innerRadius = radius / 1.7;

  const pieLayout = pie<Item>().value((d) => d.value).padAngle(gap);
  const arcGen = arc<PieArcDatum<Item>>()
    .innerRadius(innerRadius)
    .outerRadius(radius)
    .cornerRadius(12);

  const labelArc = arc<PieArcDatum<Item>>()
    .innerRadius(radius * 0.82)
    .outerRadius(radius * 0.82);

  const arcs = pieLayout(data);

  return (
    <div className="relative flex items-center justify-center">
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
        <div className="text-center">
          <p className="text-sm text-zinc-400">Total</p>
          <p className="text-4xl font-bold text-zinc-100">{total}</p>
          <p className="text-xs text-zinc-500 mt-0.5">leads</p>
        </div>
      </div>
      <svg
        viewBox={`-${radius} -${radius} ${radius * 2} ${radius * 2}`}
        className="w-56 h-56 overflow-visible"
      >
        {arcs.map((d, i) => {
          const angle = ((d.endAngle - d.startAngle) * 180) / Math.PI;
          const centroid = labelArc.centroid(d);
          return (
            <g key={i}>
              <path
                d={arcGen(d) || undefined}
                fill={data[i].color}
                fillOpacity={0.9}
                stroke="rgba(255,255,255,0.1)"
                strokeWidth={8}
              />
              {angle > 18 && (
                <text
                  transform={`translate(${centroid})`}
                  textAnchor="middle"
                  fontSize={36}
                  fill="white"
                  fontWeight={600}
                >
                  {data[i].name}
                </text>
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
}
