"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";

const NAV = [
  {
    href: "/",
    icon: "⚡",
    label: "Command Center",
    badge: null,
    color: "text-blue-400",
    ring: "rgba(99,102,241,0.3)",
  },
  {
    href: "/b2b",
    icon: "🎯",
    label: "B2B Lead Intel",
    badge: "31 leads",
    color: "text-indigo-400",
    ring: "rgba(99,102,241,0.3)",
  },
  {
    href: "/coches",
    icon: "🚗",
    label: "Arbitraje Coches",
    badge: "52 HIGH",
    color: "text-amber-400",
    ring: "rgba(245,158,11,0.3)",
  },
  {
    href: "/digital",
    icon: "📡",
    label: "Auditoría Digital",
    badge: "42 HIGH",
    color: "text-cyan-400",
    ring: "rgba(6,182,212,0.3)",
  },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 h-screen w-56 flex flex-col z-50 border-r border-white/[0.06] bg-[#060b16]/95 backdrop-blur-2xl">
      {/* Brand */}
      <div className="px-4 pt-5 pb-4 border-b border-white/[0.06]">
        <div className="flex items-center gap-3">
          <div
            className="w-8 h-8 rounded-xl flex items-center justify-center text-sm font-bold shadow-lg"
            style={{
              background: "linear-gradient(135deg, #6366f1, #3b82f6)",
              boxShadow: "0 4px 14px rgba(99,102,241,0.35)",
            }}
          >
            ⚡
          </div>
          <div>
            <p className="text-[13px] font-bold tracking-tight text-white">LeadOS</p>
            <p className="text-[10px] text-slate-500 mt-0.5">Intelligence Platform</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
        <p className="text-[9px] font-bold uppercase tracking-[0.12em] text-slate-600 px-2 mb-3">
          Pipelines
        </p>

        {NAV.map((item) => {
          const active = pathname === item.href;
          return (
            <Link key={item.href} href={item.href} className="block">
              <motion.div
                whileHover={{ x: 2 }}
                whileTap={{ scale: 0.97 }}
                transition={{ type: "spring", stiffness: 400, damping: 25 }}
                className={`
                  relative flex items-center gap-2.5 px-3 py-2.5 rounded-xl cursor-pointer
                  transition-all duration-200 select-none
                  ${active
                    ? "bg-indigo-500/[0.12] text-white"
                    : "text-slate-400 hover:text-slate-200 hover:bg-white/[0.05]"
                  }
                `}
              >
                {active && (
                  <span
                    className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 rounded-full"
                    style={{ background: "linear-gradient(180deg, #818cf8, #6366f1)" }}
                  />
                )}

                <span
                  className={`
                    w-6 h-6 rounded-lg flex items-center justify-center text-sm shrink-0
                    transition-all duration-200
                    ${active ? "bg-indigo-500/20" : "bg-white/[0.05]"}
                  `}
                >
                  {item.icon}
                </span>

                <span className={`text-[12.5px] font-medium flex-1 leading-none ${active ? "text-white" : ""}`}>
                  {item.label}
                </span>

                {item.badge && (
                  <span
                    className={`
                      text-[10px] px-1.5 py-0.5 rounded-md font-mono leading-none shrink-0
                      transition-all duration-200
                      ${active
                        ? "bg-indigo-500/25 text-indigo-300"
                        : "bg-white/[0.06] text-slate-500"
                      }
                    `}
                  >
                    {item.badge}
                  </span>
                )}
              </motion.div>
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="px-4 py-4 border-t border-white/[0.06] space-y-2">
        <div className="flex items-center gap-2">
          <span className="dot-live" />
          <span className="text-[11px] text-slate-400">Pipeline activo</span>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {["Claude Haiku", "Firecrawl", "Apify"].map((t) => (
            <span
              key={t}
              className="text-[9px] px-1.5 py-0.5 rounded-md bg-white/[0.04] text-slate-600 font-mono"
            >
              {t}
            </span>
          ))}
        </div>
      </div>
    </aside>
  );
}
