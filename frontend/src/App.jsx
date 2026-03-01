import Navbar from "./components/Navbar"
import { Link, Routes, Route } from "react-router-dom"
import Home from "./pages/Home";
import Dashboard from "./pages/Dashboard";
import SnapshotDashboard from "./pages/SnapshotPage";
import DiagnosticsInfo from "./pages/DiagnosticsPage";
import "./index.css";

const App = () => {
    return (
        <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/snapshot" element={<SnapshotDashboard />} />
            <Route path="/diagnostics" element={<DiagnosticsInfo />} />
        </Routes>
    );
}
export default App