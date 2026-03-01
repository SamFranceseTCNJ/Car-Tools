import Navbar from "../components/Navbar";
import InfoSection from "../components/InfoComponent";

const About = () => {
  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-100 to-blue-50 flex flex-col items-center">
      <Navbar />

      <div className="flex flex-col items-center flex-1 text-center px-6 mt-8 w-full max-w-3xl">
        <h1 className="text-4xl font-bold text-gray-800 mb-4">
          About This Project
        </h1>

        <p className="text-lg text-gray-600 mb-10">
          Intelligent vehicle diagnostics built to make car data understandable.
        </p>

        <div className="grid grid-cols-1 gap-6 w-full text-left">
          <InfoSection title="The Problem">
            OBD-II diagnostic codes are cryptic and inaccessible to non-experts.
            Drivers often receive error codes without context or guidance.
          </InfoSection>

          <InfoSection title="Our Solution">
            We translate raw vehicle telemetry into human-readable explanations,
            rank severity, predict causes, and suggest repair difficulty.
          </InfoSection>

          <InfoSection title="How It Works">
            Vehicle data streams from an OBD-II adapter through a Bluetooth bridge
            into the web app via WebSockets for real-time analysis.
          </InfoSection>

          <InfoSection title="Hackathon Context">
            Built during a 24-hour hackathon, this project focuses on clarity,
            technical depth, and real-world applicability.
          </InfoSection>
        </div>
      </div>
    </div>
  );
};

export default About;