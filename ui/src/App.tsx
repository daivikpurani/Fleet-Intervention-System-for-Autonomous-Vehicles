// Main App component with routing and navigation

import { useState } from "react";
import { Routes, Route } from "react-router-dom";
import { Header } from "./components/Header";
import { MainDashboard } from "./pages/MainDashboard";
import { MetricsDashboard } from "./pages/MetricsDashboard";

function App() {
  const [demoMode, setDemoMode] = useState(false);

  return (
    <div className="flex flex-col h-screen bg-white">
      <Header />
      <Routes>
        <Route path="/" element={<MainDashboard demoMode={demoMode} />} />
        <Route path="/operations" element={<MainDashboard demoMode={demoMode} />} />
        <Route path="/dashboard" element={<MainDashboard demoMode={demoMode} />} />
        <Route path="/reports" element={<MetricsDashboard />} />
        <Route path="/analytics" element={<MetricsDashboard />} />
      </Routes>
    </div>
  );
}

export default App;
