import { useMemo, useRef, useState, useEffect } from "react";

function clamp(n, min, max) {
  if (n == null || Number.isNaN(n)) return null;
  return Math.min(max, Math.max(min, n));
}

function fmt(n, digits = 0) {
  if (n == null || Number.isNaN(n)) return "—";
  return Number(n).toFixed(digits);
}

function Sparkline({ values, min, max }) {
  const points = useMemo(() => {
    const clean = values.filter((v) => v != null && !Number.isNaN(v));
    if (clean.length < 2) return "";

    const lo = min ?? Math.min(...clean);
    const hi = max ?? Math.max(...clean);
    const span = hi - lo || 1;

    const w = 120;
    const h = 28;
    const step = w / (values.length - 1);

    return values
      .map((v, i) => {
        if (v == null || Number.isNaN(v)) return null;
        const x = i * step;
        const y = h - ((v - lo) / span) * h;
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .filter(Boolean)
      .join(" ");
  }, [values, min, max]);

  return (
    <svg viewBox="0 0 120 28" className="w-[120px] h-[28px]">
      <polyline
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        points={points}
        className="text-blue-600"
      />
    </svg>
  );
}

function MetricCard({ title, value, unit, subtitle, status = "normal", spark }) {
  const statusClasses =
    status === "bad"
      ? "border-red-200 bg-red-50"
      : status === "warn"
      ? "border-yellow-200 bg-yellow-50"
      : "border-gray-200 bg-white";

  return (
    <div className={`rounded-lg border ${statusClasses} p-4 shadow-sm`}>
      <div className="text-sm text-gray-600 flex items-center justify-between gap-3">
        <span>{title}</span>
        {spark}
      </div>
      <div className="mt-2 flex items-baseline gap-2">
        <div className="text-3xl font-semibold text-gray-900">{value}</div>
        <div className="text-sm text-gray-500">{unit}</div>
      </div>
      {subtitle ? <div className="mt-1 text-xs text-gray-500">{subtitle}</div> : null}
    </div>
  );
}

function BarCard({ title, valuePct, colorClass = "bg-blue-600", hint }) {
  const v = valuePct == null ? null : clamp(Number(valuePct), 0, 100);

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm text-left">
      <div className="text-sm text-gray-600 flex justify-between">
        <span>{title}</span>
        <span className="text-xs text-gray-500">{v == null ? "—" : `${v.toFixed(0)}%`}</span>
      </div>
      <div className="mt-2 h-2 w-full rounded bg-gray-200 overflow-hidden">
        <div
          className={`h-2 ${colorClass}`}
          style={{ width: v == null ? "0%" : `${v.toFixed(0)}%` }}
        />
      </div>
      {hint ? <div className="mt-2 text-xs text-gray-500">{hint}</div> : null}
    </div>
  );
}

const Fuel_Air_Metrics_Dashboard = () => {
  const [history, setHistory] = useState([]);
  const wsRef = useRef(null);

  useEffect(() => {
    if (wsRef.current) return;

    const ws = new WebSocket("ws://127.0.0.1:8765");
    wsRef.current = ws;

    ws.onopen = () => console.log("WebSocket connected");

    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data);

      if (msg?.type !== "fuel_air") return;

      const data = msg.data;
      setHistory((prev) => [...prev, data].slice(-120));
    };

    ws.onerror = (e) => console.error("WebSocket error", e);

    ws.onclose = () => {
      console.log("WebSocket closed");
      wsRef.current = null;
    };
  }, []);

  const latest = history.length ? history[history.length - 1] : null;
  const series = (key) =>
    history.map((m) => (m?.[key] == null ? null : Number(m[key])));

 
  return (
    <div className="w-full grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 grid grid-cols-1 sm:grid-cols-2 gap-4">
        <MetricCard
            title="Mass Air Flow g/s"
            value={fmt(latest?.maf_gps, 2)}
            unit="(grams / sec)"
            spark={<Sparkline values={series("fuel_rate")} />}
        />

        <MetricCard
            title="Fuel Rate"
            value={fmt(latest?.fuel_rate, 2)}
            unit="(unit from bridge)"
            subtitle="Consumption rate"
            spark={<Sparkline values={series("fuel_rate")} />}
        />

        <MetricCard
            title="Short Term Fuel Trim Bank 1"
            value={fmt(latest?.short_term_fuel_trim_B1, 2)}
        />

        <MetricCard
            title="Long Term Fuel Trim Bank 1"
            value={fmt(latest?.long_term_fuel_trim_B1, 2)}
        />

        <MetricCard
            title="Short Term Fuel Trim Bank 2"
            value={fmt(latest?.short_term_fuel_trim_B2, 2)}
        />

        <MetricCard
            title="Long Term Fuel Trim Bank 2"
            value={fmt(latest?.long_term_fuel_trim_B2, 2)}
        />

        </div>
    </div>
  );
};

export default Fuel_Air_Metrics_Dashboard;