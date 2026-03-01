import { useState } from "react";
import Navbar from "../components/Navbar";
import Live_Metrics_Dashboard from "./subpages/Live_Metrics";
import Engine_Metrics_Dashboard from "./subpages/Engine_Metrics";
import Fuel_Air_Metrics_Dashboard from "./subpages/Fuel_Air_Metrics";
import Status_Metrics_Dashboard from "./subpages/Status_Metrics";

const Dashboard = () => {
  const [active, setActive] = useState("live");

  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-100 to-blue-50 flex flex-col items-center">
      <Navbar />

      <div className="w-full max-w-6xl px-6 mt-8">
        <div className="flex flex-wrap justify-center gap-2">
          <button
            className={`px-3 py-1 rounded border ${active === "live" ? "bg-white" : "bg-transparent"}`}
            onClick={() => setActive("live")}
          >
            Driving
          </button>
          <button
            className={`px-3 py-1 rounded border ${active === "engine" ? "bg-white" : "bg-transparent"}`}
            onClick={() => setActive("engine")}
          >
            Engine
          </button>
          <button
            className={`px-3 py-1 rounded border ${active === "fuelair" ? "bg-white" : "bg-transparent"}`}
            onClick={() => setActive("fuelair")}
          >
            Fuel/Air
          </button>
          <button
            className={`px-3 py-1 rounded border ${active === "status" ? "bg-white" : "bg-transparent"}`}
            onClick={() => setActive("status")}
          >
            Status
          </button>
        </div>

        <div className="mt-8 w-full">
          {active === "live" && <Live_Metrics_Dashboard />}
          {active === "engine" && <Engine_Metrics_Dashboard />}
          {active === "fuelair" && <Fuel_Air_Metrics_Dashboard />}
          {active === "status" && <Status_Metrics_Dashboard />}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;