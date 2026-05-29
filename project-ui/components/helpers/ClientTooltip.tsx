"use client";
import * as React from "react";
import { createPortal } from "react-dom";

type TooltipContextValue = {
  tooltip: { x: number; y: number } | undefined;
  setTooltip: (tooltip: { x: number; y: number } | undefined) => void;
};

const TooltipContext = React.createContext<TooltipContextValue | undefined>(undefined);

function useTooltipContext(componentName: string): TooltipContextValue {
  const context = React.useContext(TooltipContext);
  if (!context) throw new Error(`Wrap in ClientTooltip: ${componentName}`);
  return context;
}

const Tooltip: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [tooltip, setTooltip] = React.useState<{ x: number; y: number }>();
  return (
    <TooltipContext.Provider value={{ tooltip, setTooltip }}>
      {children}
    </TooltipContext.Provider>
  );
};

const TooltipTrigger = React.forwardRef<SVGGElement, { children: React.ReactNode }>(
  (props, forwardedRef) => {
    const context = useTooltipContext("TooltipTrigger");
    const triggerRef = React.useRef<SVGGElement | null>(null);
    React.useEffect(() => {
      const fn = (e: MouseEvent | TouchEvent) => {
        if (triggerRef.current && !triggerRef.current.contains(e.target as Node))
          context.setTooltip(undefined);
      };
      document.addEventListener("mousedown", fn);
      return () => document.removeEventListener("mousedown", fn);
    }, [context]);
    return (
      <g
        ref={(n) => {
          triggerRef.current = n;
          if (typeof forwardedRef === "function") forwardedRef(n);
          else if (forwardedRef) forwardedRef.current = n;
        }}
        onPointerMove={(e) => { if (e.pointerType === "mouse") context.setTooltip({ x: e.clientX, y: e.clientY }); }}
        onPointerLeave={(e) => { if (e.pointerType === "mouse") context.setTooltip(undefined); }}
      >
        {props.children}
      </g>
    );
  }
);
TooltipTrigger.displayName = "TooltipTrigger";

const TooltipContent = React.forwardRef<HTMLDivElement, { children: React.ReactNode }>(
  (props, _) => {
    const context = useTooltipContext("TooltipContent");
    const ref = React.useRef<HTMLDivElement>(null);
    if (!context.tooltip || typeof document === "undefined") return null;
    const tw = ref.current?.offsetWidth ?? 0;
    const overflow = context.tooltip.x + tw + 10 > window.innerWidth;
    return createPortal(
      <div
        ref={ref}
        className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 px-3.5 py-2 rounded fixed z-50 text-sm"
        style={{
          top: context.tooltip.y - 20,
          left: overflow ? context.tooltip.x - tw - 10 : context.tooltip.x + 10,
        }}
      >
        {props.children}
      </div>,
      document.body
    );
  }
);
TooltipContent.displayName = "TooltipContent";

export { Tooltip as ClientTooltip, TooltipTrigger, TooltipContent };
