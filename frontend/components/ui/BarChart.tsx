type BarChartItem = {
  label: string;
  value: number;
  colorClass?: string; // Tailwind bg-* class, e.g. "bg-brand"
};

type BarChartProps = {
  data: BarChartItem[];
  /** Override the 100% reference value. Defaults to max of the data. */
  max?: number;
  /** Show value labels on the right. Defaults to true. */
  showValues?: boolean;
};

export function BarChart({ data, max, showValues = true }: BarChartProps) {
  const peak = max ?? Math.max(...data.map((d) => d.value), 1);

  return (
    <div className="space-y-2.5">
      {data.map((item) => {
        const pct = peak === 0 ? 0 : Math.round((item.value / peak) * 100);
        return (
          <div key={item.label} className="flex items-center gap-3">
            <span className="w-28 shrink-0 truncate text-right text-xs text-muted">
              {item.label}
            </span>

            <div className="relative flex-1 overflow-hidden rounded-full bg-border" style={{ height: 10 }}>
              <div
                className={`absolute left-0 top-0 h-full rounded-full transition-all duration-500 ${item.colorClass ?? "bg-brand"}`}
                style={{ width: `${pct}%` }}
                role="presentation"
              />
            </div>

            {showValues && (
              <span className="w-7 shrink-0 text-right text-xs tabular-nums text-muted">
                {item.value}
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}
