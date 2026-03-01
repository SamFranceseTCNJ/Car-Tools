import { useState, useRef } from "react";
import Navbar from "../components/Navbar";

const DiagnosticsInfo = () => {
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [lastRunAt, setLastRunAt] = useState(null);

  async function runDiagnostics() {
    setIsRunning(true);
    setError("");
    setResult(null);

    try {
      const res = await fetch("http://127.0.0.1:8080/api/diagnostics/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json" }
      });

      if (!res.ok) {
        const text = await res.text().catch(() => "");
        throw new Error(`Diagnostics failed (${res.status}). ${text}`.trim());
      }

      const data = await res.json();
      setResult(data);
      setLastRunAt(new Date());
    } catch (e) {
      setError(e?.message ?? "Diagnostics failed.");
    } finally {
      setIsRunning(false);
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-100 to-blue-50 flex flex-col items-center">
      <Navbar />

      <div className="w-full max-w-6xl px-6 mt-8">
        <div className="flex items-center justify-between gap-4">
          <h1 className="text-2xl font-semibold text-gray-900">Diagnostics</h1>

          <button
            onClick={runDiagnostics}
            disabled={isRunning}
            className={`px-4 py-2 rounded-md border shadow-sm ${
              isRunning ? "opacity-60 cursor-not-allowed" : "bg-white hover:bg-gray-50"
            }`}
          >
            {isRunning ? "Running…" : "Run Diagnostics"}
          </button>
        </div>

        {lastRunAt && (
          <div className="mt-2 text-sm text-gray-600">
            Last run: {lastRunAt.toLocaleString()}
          </div>
        )}

        {error && (
          <div className="mt-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {error}
          </div>
        )}

        <div className="mt-6 rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
          <div className="text-sm font-medium text-gray-700">Results</div>

          {!result && !error && (
            <div className="mt-2 text-sm text-gray-500">
              Click “Run Diagnostics” to fetch the latest results.
            </div>
          )}

          {result && (
            <pre className="mt-3 text-xs overflow-auto bg-gray-50 p-3 rounded border border-gray-100">
              {JSON.stringify(result, null, 2)}
            </pre>
          )}
        </div>
      </div>
    </div>
  );
}

export default DiagnosticsInfo;