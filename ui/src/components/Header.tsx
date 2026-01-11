import { useState, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { motion } from "framer-motion";
import { MessageSquare, Settings, Plus, ChevronDown, Play } from "lucide-react";
import { Tabs, TabsList, TabsTrigger } from "./ui/tabs";
import { cn } from "../lib/utils";

export function Header() {
  const location = useLocation();
  const navigate = useNavigate();
  const [currentTime, setCurrentTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString("en-US", {
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
    });
  };

  const getActiveTab = () => {
    if (location.pathname === "/" || location.pathname === "/operations") {
      return "operations";
    }
    if (location.pathname === "/analytics" || location.pathname === "/reports") {
      return "reports";
    }
    return "dashboard";
  };

  return (
    <header className="h-14 border-b border-border bg-white flex items-center justify-between px-6">
      {/* Left: Logo and Navigation */}
      <div className="flex items-center gap-4">
        {/* FleetOps Logo */}
        <div className="flex items-center gap-2">
          <div className="relative w-8 h-8 flex items-center justify-center">
            <div className="absolute inset-0 bg-blue-600 rounded flex items-center justify-center">
              <Play className="w-4 h-4 text-white fill-white" />
            </div>
            <div className="absolute -top-0.5 -right-0.5 w-3 h-3 bg-blue-500 rounded-full" />
          </div>
          <span className="text-lg font-bold text-gray-900">FleetOps</span>
        </div>

        {/* Navigation Tabs */}
        <Tabs value={getActiveTab()} onValueChange={(value) => {
          if (value === "dashboard") navigate("/dashboard");
          else if (value === "operations") navigate("/");
          else if (value === "reports") navigate("/reports");
        }}>
          <TabsList className="bg-transparent h-auto p-0 gap-1">
            <TabsTrigger
              value="dashboard"
              className={cn(
                "px-4 py-1.5 text-sm font-semibold rounded-md",
                "data-[state=active]:bg-blue-50 data-[state=active]:text-blue-600 data-[state=active]:border data-[state=active]:border-blue-200",
                "data-[state=inactive]:text-gray-600 hover:text-gray-900"
              )}
            >
              Dashboard
            </TabsTrigger>
            <TabsTrigger
              value="operations"
              className={cn(
                "px-4 py-1.5 text-sm font-semibold rounded-md",
                "data-[state=active]:bg-blue-50 data-[state=active]:text-blue-600 data-[state=active]:border data-[state=active]:border-blue-200",
                "data-[state=inactive]:text-gray-600 hover:text-gray-900"
              )}
            >
              Operations
            </TabsTrigger>
            <TabsTrigger
              value="reports"
              className={cn(
                "px-4 py-1.5 text-sm font-semibold rounded-md",
                "data-[state=active]:bg-blue-50 data-[state=active]:text-blue-600 data-[state=active]:border data-[state=active]:border-blue-200",
                "data-[state=inactive]:text-gray-600 hover:text-gray-900"
              )}
            >
              Reports
            </TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      {/* Right: Icons, User Profile, Time */}
      <div className="flex items-center gap-3">
        {/* Icons */}
        <motion.button
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.95 }}
          className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-md transition-colors"
        >
          <MessageSquare className="w-5 h-5" />
        </motion.button>
        <motion.button
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.95 }}
          className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-md transition-colors"
        >
          <Settings className="w-5 h-5" />
        </motion.button>
        <motion.button
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.95 }}
          className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-md transition-colors"
        >
          <Plus className="w-5 h-5" />
        </motion.button>

        {/* Number with arrow */}
        <div className="flex items-center gap-1 px-2 py-1 bg-gray-50 rounded-md">
          <span className="text-sm font-semibold text-gray-900">60</span>
          <ChevronDown className="w-4 h-4 text-gray-600" />
        </div>

        {/* User Profile */}
        <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-white text-sm font-semibold">
          U
        </div>

        {/* Time */}
        <div className="px-3 py-1.5 bg-gray-50 rounded-md">
          <span className="text-sm font-semibold text-gray-900 font-mono">
            {formatTime(currentTime)}
          </span>
        </div>
      </div>
    </header>
  );
}
