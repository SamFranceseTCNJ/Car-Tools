import Navbar from "./components/Navbar"
import { Link, Routes, Route } from "react-router-dom"
import Home from "./pages/Home";
import Dashboard from "./pages/Dashboard";
import "./index.css";

const App = () => {
    return (
        <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/dashboard" element={<Dashboard />} />
        </Routes>
    );
}
export default App