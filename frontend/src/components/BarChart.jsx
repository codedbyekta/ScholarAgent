export default function BarChart({ data, labelKey, valueKey, valueFormatter, color = "#2563eb" }) {
  const maxValue = Math.max(...data.map((d) => d[valueKey] ?? 0), 0.0001);

  return (
    <div className="space-y-2">
      {data.map((d, i) => {
        const value = d[valueKey];
        const widthPct = value === null || value === undefined ? 0 : (value / maxValue) * 100;
        return (
          <div key={i} className="flex items-center gap-2 text-xs">
            <div className="w-28 shrink-0 truncate text-gray-400" title={d[labelKey]}>
              {d[labelKey]}
            </div>
            <div className="flex-1 bg-[#1a1d27] rounded h-4 overflow-hidden">
              <div
                className="h-4 rounded"
                style={{ width: `${widthPct}%`, backgroundColor: color }}
              />
            </div>
            <div className="w-16 text-right text-gray-300">
              {value === null || value === undefined
                ? "N/A"
                : valueFormatter
                ? valueFormatter(value)
                : value.toFixed(2)}
            </div>
          </div>
        );
      })}
    </div>
  );
}
