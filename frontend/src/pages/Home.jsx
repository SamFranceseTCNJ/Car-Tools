import Navbar from "../components/Navbar";

const Home = () => {
  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-100 to-blue-50 flex flex-col items-center">
      <Navbar />

      <div className="flex flex-col items-center justify-center flex-1 text-center px-6">
        <h1 className="text-5xl sm:text-6xl font-extrabold text-gray-800 mb-6">
          Diagnose Your Car, Intelligently
        </h1>
        <p className="text-lg sm:text-xl text-gray-700 mb-8 max-w-2xl">
          Get human-friendly explanations of your OBD-II codes, severity ranking, 
          likely causes, and repair difficulty — all in real-time.
        </p>

        <div className="flex flex-col sm:flex-row gap-4">
          <a href="/dashboard">
            <button className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-6 rounded shadow transition">
                Get Started
            </button>
          </a>
          <a href="/about">
            <button className="bg-white hover:bg-gray-100 border border-gray-300 text-gray-800 font-semibold py-3 px-6 rounded shadow transition">
                Learn More
            </button>
          </a>
        </div>
      </div>
    </div>
  );
};

export default Home;