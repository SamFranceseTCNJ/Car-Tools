import { useState, useRef } from "react";
import Navbar from "../components/Navbar";

const DiagnosticsInfo = () => {
  const [diagnosticsRunning, setDiagnosticsRunning] = useState(false);
  const [messages, setMessages] = useState([]);
  const wsRef = useRef(null);

  const startDiagnostics = () => {
    if (wsRef.current) return;

    const ws = new WebSocket("ws://127.0.0.1:8765");
    wsRef.current = ws;
    setDiagnosticsRunning(true);

    ws.onopen = () => console.log("WebSocket connected");

    ws.onmessage = (e) => {
      const data = JSON.parse(e.data);

      // data shape matches mock_bridge.py exactly
      setMessages((prev) => [data, ...prev].slice(0, 20));
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

  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-100 to-blue-50 flex flex-col items-center">
      <Navbar />

      <div className="flex flex-col items-center flex-1 text-center px-6 mt-8 w-full max-w-3xl">
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
          <div className="mt-8 grid grid-cols-1 sm:grid-cols-2 gap-6 w-full">
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

      </div>
    </div>
  );
};

export default DiagnosticsInfo;