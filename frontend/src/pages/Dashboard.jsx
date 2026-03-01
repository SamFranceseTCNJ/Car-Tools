import { useState } from 'react';
import Navbar from "../components/Navbar";

const Dashboard = () => {
  const [diagnosticsRunning, setDiagnosticsRunning] = useState(false);

  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-100 to-blue-50 flex flex-col items-center">
      <Navbar />

      <div className="flex flex-col items-center justify-center flex-1 text-center px-6 mt-8 w-full max-w-3xl">

        <button
          onClick={() => setDiagnosticsRunning(true)}
          className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-6 rounded shadow transition"
        >
          Run Diagnostics
        </button>

        {diagnosticsRunning && (
          <div className="mt-8 grid grid-cols-1 sm:grid-cols-2 gap-6 w-full">
            {/* Example buttons that show after running diagnostics */}
            <button className="bg-blue-400 hover:bg-blue-600 text-white font-semibold py-3 px-6 rounded shadow transition">
              View DTCs
            </button>
            <button className="bg-blue-400 hover:bg-blue-600 text-white font-semibold py-3 px-6 rounded shadow transition">
              Rank Severity
            </button>
            <button className="bg-blue-400 hover:bg-blue-600 text-white font-semibold py-3 px-6 rounded shadow transition">
              Predict Causes
            </button>
            <button className="bg-blue-400 hover:bg-blue-600 text-white font-semibold py-3 px-6 rounded shadow transition">
              Suggest Repair Difficulty
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default Dashboard;