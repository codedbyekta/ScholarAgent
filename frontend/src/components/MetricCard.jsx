function formatPercent(value) {
  if (value === null || value === undefined) return "Not evaluated";
  return `${(value * 100).toFixed(1)}%`;
}

function formatMs(value) {
  if (value === null || value === undefined) return "Not evaluated";
  return `${value.toFixed(0)} ms`;
}

export default function MetricCard({ label, value, kind = "percent", tone = "neutral" }) {
  const display = kind === "ms" ? formatMs(value) : formatPercent(value);
  const isMissing = value === null || value === undefined;

  const toneClasses = isMissing
    ? "text-gray-500"
    : tone === "good"
    ? "text-green-400"
    : tone === "bad"
    ? "text-red-400"
    : "text-gray-100";

  return (
    <div className="bg-panel border border-border rounded-lg p-4">
      <div className="text-xs text-gray-400 mb-1">{label}</div>
      <div className={`text-2xl font-semibold ${toneClasses}`}>{display}</div>
    </div>
  );
}

export { formatPercent, formatMs };
