import { useEffect, useState } from "react";
import Navbar from "../components/Navbar";

const API_URL = "http://127.0.0.1:8080/api/snapshot";

const SnapshotDashboard = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  const fetchSnapshot = async () => {
    setLoading(true);
    try {
      const res = await fetch(API_URL);
      const json = await res.json();
      setData(json);
    } catch (err) {
      console.error("API error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSnapshot();
    const id = setInterval(fetchSnapshot, 2000);
    return () => clearInterval(id);
  }, []);

  const fmt = (n, digits = 0) =>
    n == null || Number.isNaN(n) ? "—" : Number(n).toFixed(digits);

  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-100 to-blue-50 flex flex-col items-center">
      <Navbar />

      <div className="flex flex-col items-center w-full max-w-6xl px-6 py-12 space-y-10">

        {/* Header */}
        <div className="text-center">
          <h1 className="text-4xl sm:text-5xl font-extrabold text-gray-800 mb-4">
            Vehicle Snapshot
          </h1>
          <p className="text-lg text-gray-700">
            Real-time telemetry pulled directly from your ECU.
          </p>
        </div>

        {/* Refresh Button */}
        <button
          onClick={fetchSnapshot}
          className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-6 rounded shadow transition"
        >
          {loading ? "Refreshing..." : "Refresh Now"}
        </button>

        {/* Metrics Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 w-full">

          {/* Live Metrics */}
          <div className="bg-white rounded-lg shadow p-6 text-center">
            <h2 className="text-xl font-bold text-gray-800 mb-4">Live</h2>
            <p className="text-2xl font-semibold text-gray-900">
              {fmt(data?.live?.rpm)} rpm
            </p>
            <p className="text-gray-600">
              Speed: {fmt(data?.live?.speed_kph)} km/h
            </p>
            <p className="text-gray-600">
              Throttle: {fmt(data?.live?.throttle_position)} %
            </p>
            <p className="text-gray-600">
              Engine Load: {fmt(data?.live?.engine_load)} %
            </p>
          </div>

          {/* Engine Metrics */}
          <div className="bg-white rounded-lg shadow p-6 text-center">
            <h2 className="text-xl font-bold text-gray-800 mb-4">Engine</h2>
            <p className="text-gray-700">
              Coolant Temp: {fmt(data?.engine?.coolant_temp)} °C
            </p>
            <p className="text-gray-700">
              Intake Air Temp: {fmt(data?.engine?.intake_air_temp_c)} °C
            </p>
            <p className="text-gray-700">
              Timing Advance: {fmt(data?.engine?.timing_advance_deg, 1)} °
            </p>
          </div>

          {/* Fuel & Air */}
          <div className="bg-white rounded-lg shadow p-6 text-center">
            <h2 className="text-xl font-bold text-gray-800 mb-4">Fuel & Air</h2>
            <p className="text-gray-700">
              MAF: {fmt(data?.fuel_air?.maf_gps, 2)} g/s
            </p>
            <p className="text-gray-700">
              STFT B1: {fmt(data?.fuel_air?.short_term_fuel_trim_B1, 1)} %
            </p>
            <p className="text-gray-700">
              LTFT B1: {fmt(data?.fuel_air?.long_term_fuel_trim_B1, 1)} %
            </p>
            <p className="text-gray-700">
              Fuel Rate: {fmt(data?.fuel_air?.fuel_rate, 2)} L/h
            </p>
          </div>

          {/* Status */}
          <div className="bg-white rounded-lg shadow p-6 text-center">
            <h2 className="text-xl font-bold text-gray-800 mb-4">Status</h2>
            <p className="text-gray-700">
              Fuel Level: {fmt(data?.status?.fuel_level)} %
            </p>
            <p className="text-gray-700">
              Voltage: {fmt(data?.status?.control_module_voltage, 2)} V
            </p>
          </div>

          {/* Diagnostics */}
          <div className="bg-white rounded-lg shadow p-6 text-center md:col-span-2">
            <h2 className="text-xl font-bold text-gray-800 mb-4">Diagnostics</h2>

            {Array.isArray(data?.diagnostics?.dtcs) && data.diagnostics.dtcs.length > 0 ? (
              <ul className="text-gray-800 font-mono space-y-2 text-left">
                {data.diagnostics.dtcs.map((dtc, i) => {
                  const isObj = dtc && typeof dtc === "object";
                  const code = isObj ? dtc.code : String(dtc);
                  const status = isObj ? dtc.status : null;
                  const description = isObj ? dtc.description : null;

                  return (
                    <li
                      key={`${code ?? "dtc"}-${i}`}
                      className="rounded border border-gray-200 bg-gray-50 p-3"
                    >
                      <div className="flex items-center justify-between gap-3">
                        <span className="font-semibold">{code ?? "Unknown code"}</span>
                        {status ? (
                          <span className="text-xs text-gray-600">{status}</span>
                        ) : null}
                      </div>
                      {description ? (
                        <div className="mt-1 text-sm text-gray-700 font-sans">
                          {description}
                        </div>
                      ) : null}
                    </li>
                  );
                })}
              </ul>
            ) : (
              <p className="text-gray-600">No active trouble codes detected.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default SnapshotDashboard;