import { Loader2 } from "lucide-react";

type ChartSkeletonProps = {
  className?: string;
  label?: string;
};

export function ChartSkeleton({ className = "", label = "Loading chart data..." }: ChartSkeletonProps) {
  return (
    <div
      className={`relative flex h-full w-full items-center justify-center overflow-hidden rounded-md border border-slate-200 bg-slate-50 ${className}`}
      aria-busy="true"
      aria-live="polite"
    >
      <div className="absolute inset-0 opacity-70">
        <div className="absolute left-4 right-4 top-4 h-px bg-slate-200" />
        <div className="absolute left-4 right-4 top-16 h-px bg-slate-200" />
        <div className="absolute left-4 right-4 top-28 h-px bg-slate-200" />
        <div className="absolute left-4 right-4 top-40 h-px bg-slate-200" />
        <div className="absolute bottom-5 left-8 right-5 h-px bg-slate-300" />
      </div>
      <div className="relative z-10 flex items-center gap-2 rounded-full bg-white/90 px-3 py-1 text-xs text-slate-600 shadow-sm">
        <Loader2 className="h-3.5 w-3.5 animate-spin" />
        <span>{label}</span>
      </div>
    </div>
  );
}

type ChartRefreshingOverlayProps = {
  active: boolean;
};

export function ChartRefreshingOverlay({ active }: ChartRefreshingOverlayProps) {
  return (
    <div
      className={`pointer-events-none absolute right-3 top-3 z-10 inline-flex items-center gap-1.5 rounded-full bg-white/90 px-2.5 py-1 text-[11px] font-medium text-slate-600 shadow-sm transition-all duration-200 ${
        active ? "translate-y-0 opacity-100" : "-translate-y-1 opacity-0"
      }`}
      aria-live="polite"
    >
      <Loader2 className="h-3.5 w-3.5 animate-spin" />
      Refreshing
    </div>
  );
}
