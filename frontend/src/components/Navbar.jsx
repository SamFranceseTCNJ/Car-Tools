import { Link } from "react-router-dom";

const Navbar = () => {
  return (
    <nav className="bg-blue-900 text-white shadow-md w-full px-6 py-4 flex justify-between items-center">
      <div className="text-xl font-bold">Car Tools</div>

      <div className="space-x-6">
        <Link
          to="/"
          className="hover:text-blue-300 transition font-medium"
        >
          Home
        </Link>
        <Link
          to="/about"
          className="hover:text-blue-300 transition font-medium"
        >
          About
        </Link>
        <Link
          to="/dashboard"
          className="hover:text-blue-300 transition font-medium"
        >
          Dashboard
        </Link>
        <Link
          to="/snapshot"
          className="hover:text-blue-300 transition font-medium"
        >
          Snapshots
        </Link>
        <Link
          to="/diagnostics"
          className="hover:text-blue-300 transition font-medium"
        >
          Diagnostics
        </Link>
      </div>
    </nav>
  );
};

export default Navbar;