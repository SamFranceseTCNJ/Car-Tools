import { useMemo, useRef, useState } from "react";
import Navbar from "../components/Navbar";

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

const Dashboard = () => {
  const [diagnosticsRunning, setDiagnosticsRunning] = useState(false);
  const [messages, setMessages] = useState([]);
  const [history, setHistory] = useState([]);
  const wsRef = useRef(null);

  const startDiagnostics = () => {
    if (wsRef.current) return;

    const ws = new WebSocket("ws://127.0.0.1:8765");
    wsRef.current = ws;
    setDiagnosticsRunning(true);

    ws.onopen = () => console.log("WebSocket connected");

    ws.onmessage = (e) => {
      const data = JSON.parse(e.data);
      setMessages((prev) => [data, ...prev].slice(0, 20));
      setHistory((prev) => [...prev, data].slice(-120));
    };

    ws.onerror = (e) => console.error("WebSocket error", e);

    ws.onclose = () => {
      console.log("WebSocket closed");
      wsRef.current = null;
      setDiagnosticsRunning(false);
    };
  };

  const stopDiagnostics = () => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  };

  const latest = history.length ? history[history.length - 1] : null;
  const series = (key) =>
    history.map((m) => (m?.[key] == null ? null : Number(m[key])));

  // Light-touch alerting (tune thresholds)
  const coolant = latest?.coolant_temp == null ? null : Number(latest.coolant_temp);
  const coolantStatus =
    coolant == null ? "normal" : coolant >= 110 ? "bad" : coolant >= 103 ? "warn" : "normal";

  const volts =
    latest?.control_module_voltage == null ? null : Number(latest.control_module_voltage);
  const voltStatus =
    volts == null
      ? "normal"
      : volts < 12.0
      ? "bad"
      : volts < 12.6
      ? "warn"
      : volts > 15.2
      ? "warn"
      : "normal";

  const fuel = latest?.fuel_level == null ? null : Number(latest.fuel_level);
  const fuelStatus = fuel == null ? "normal" : fuel <= 15 ? "warn" : "normal";

  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-100 to-blue-50 flex flex-col items-center">
      <Navbar />

      <div className="flex flex-col items-center flex-1 text-center px-6 mt-8 w-full max-w-6xl">
        {!diagnosticsRunning ? (
          <button
            onClick={startDiagnostics}
            className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-6 rounded shadow"
          >
            Run Diagnostics
          </button>
        ) : (
          <button
            onClick={stopDiagnostics}
            className="bg-red-600 hover:bg-red-700 text-white font-semibold py-3 px-6 rounded shadow"
          >
            Stop Diagnostics
          </button>
        )}

        {diagnosticsRunning && (
          <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 w-full">
            <button className="bg-blue-400 hover:bg-blue-600 text-white py-3 px-6 rounded shadow">
              View DTCs
            </button>
            <button className="bg-blue-400 hover:bg-blue-600 text-white py-3 px-6 rounded shadow">
              Rank Severity
            </button>
            <button className="bg-blue-400 hover:bg-blue-600 text-white py-3 px-6 rounded shadow">
              Predict Causes
            </button>
            <button className="bg-blue-400 hover:bg-blue-600 text-white py-3 px-6 rounded shadow">
              Suggest Repair Difficulty
            </button>
          </div>
        )}

        {/* Dashboard */}
        <div className="mt-8 w-full grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 grid grid-cols-1 sm:grid-cols-2 gap-4">
            <MetricCard
              title="RPM"
              value={fmt(latest?.rpm, 0)}
              unit="rpm"
              subtitle="Engine speed"
              spark={<Sparkline values={series("rpm")} min={0} max={7000} />}
            />
            <MetricCard
              title="Speed"
              value={fmt(latest?.speed_kph, 0)}
              unit="km/h"
              subtitle="Vehicle speed"
              spark={<Sparkline values={series("speed_kph")} min={0} max={240} />}
            />

            <BarCard
              title="Throttle Position"
              valuePct={latest?.throttle_position}
              colorClass="bg-blue-600"
              hint="0–100% driver throttle input."
            />
            <BarCard
              title="Engine Load"
              valuePct={latest?.engine_load}
              colorClass="bg-indigo-600"
              hint="0–100% calculated load."
            />

            <MetricCard
              title="Coolant Temp"
              value={fmt(latest?.coolant_temp, 0)}
              unit="°C"
              subtitle="Engine temperature"
              status={coolantStatus}
              spark={<Sparkline values={series("coolant_temp")} min={0} max={130} />}
            />
            <MetricCard
              title="Module Voltage"
              value={fmt(latest?.control_module_voltage, 1)}
              unit="V"
              subtitle="Battery/charging system"
              status={voltStatus}
              spark={<Sparkline values={series("control_module_voltage")} min={10} max={16} />}
            />

            <MetricCard
              title="Fuel Level"
              value={fmt(latest?.fuel_level, 0)}
              unit="%"
              subtitle="Estimated tank level"
              status={fuelStatus}
              spark={<Sparkline values={series("fuel_level")} min={0} max={100} />}
            />
            <MetricCard
              title="Fuel Rate"
              value={fmt(latest?.fuel_rate, 2)}
              unit="(unit from bridge)"
              subtitle="Consumption rate"
              spark={<Sparkline values={series("fuel_rate")} />}
            />
          </div>

          {/* Right column: raw feed */}
          <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm text-left">
            <div className="text-sm font-semibold text-gray-800">Live Telemetry Feed</div>
            <div className="mt-3 space-y-3 max-h-[520px] overflow-auto pr-1">
              {messages.map((msg, idx) => (
                <div key={idx} className="border rounded-md p-3 bg-gray-50">
                  <div className="text-xs text-gray-500">
                    {new Date(msg.ts).toLocaleTimeString()}
                  </div>
                  <div className="text-sm font-semibold text-gray-800">
                    RPM: {msg.rpm ?? "—"} | Speed: {msg.speed_kph ?? "—"} km/h
                  </div>
                  <div className="text-[11px] text-gray-500 mt-1">
                    Raw: {JSON.stringify(msg.raw)}
                  </div>
                </div>
              ))}
              {!messages.length ? (
                <div className="text-sm text-gray-500">No messages yet.</div>
              ) : null}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;