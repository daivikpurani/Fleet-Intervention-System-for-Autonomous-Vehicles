// Theme context for dark mode support - Mission Control aesthetic

import { createContext, useContext, useState, useEffect, ReactNode } from "react";

export type ThemeMode = "light" | "dark";

interface Theme {
  mode: ThemeMode;
  colors: {
    background: string;
    surface: string;
    surfaceSecondary: string;
    surfaceElevated: string;
    border: string;
    borderSubtle: string;
    text: string;
    textSecondary: string;
    textMuted: string;
    primary: string;
    primaryMuted: string;
    success: string;
    successMuted: string;
    warning: string;
    warningMuted: string;
    error: string;
    errorMuted: string;
    critical: string;
    criticalMuted: string;
    info: string;
    infoMuted: string;
    hover: string;
    selected: string;
    accent: string;
    accentSecondary: string;
  };
  fonts: {
    mono: string;
    display: string;
  };
}

// Light theme - Clean, professional operations center
const lightTheme: Theme = {
  mode: "light",
  colors: {
    background: "#f8fafc",
    surface: "#ffffff",
    surfaceSecondary: "#f1f5f9",
    surfaceElevated: "#ffffff",
    border: "#e2e8f0",
    borderSubtle: "#f1f5f9",
    text: "#0f172a",
    textSecondary: "#475569",
    textMuted: "#94a3b8",
    primary: "#0ea5e9",
    primaryMuted: "#e0f2fe",
    success: "#10b981",
    successMuted: "#d1fae5",
    warning: "#f59e0b",
    warningMuted: "#fef3c7",
    error: "#ef4444",
    errorMuted: "#fee2e2",
    critical: "#dc2626",
    criticalMuted: "#fecaca",
    info: "#3b82f6",
    infoMuted: "#dbeafe",
    hover: "#f1f5f9",
    selected: "#e0f2fe",
    accent: "#8b5cf6",
    accentSecondary: "#06b6d4",
  },
  fonts: {
    mono: "'JetBrains Mono', 'SF Mono', 'Fira Code', monospace",
    display: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
  },
};

// Dark theme - Mission control / AV operations aesthetic
const darkTheme: Theme = {
  mode: "dark",
  colors: {
    background: "#0a0e14",
    surface: "#0f1419",
    surfaceSecondary: "#1a1f26",
    surfaceElevated: "#1f252d",
    border: "#2d3640",
    borderSubtle: "#1f252d",
    text: "#e6e9ed",
    textSecondary: "#9ca3af",
    textMuted: "#6b7280",
    primary: "#22d3ee",
    primaryMuted: "#164e63",
    success: "#34d399",
    successMuted: "#064e3b",
    warning: "#fbbf24",
    warningMuted: "#78350f",
    error: "#f87171",
    errorMuted: "#7f1d1d",
    critical: "#ef4444",
    criticalMuted: "#991b1b",
    info: "#60a5fa",
    infoMuted: "#1e3a8a",
    hover: "#1f252d",
    selected: "#164e63",
    accent: "#a78bfa",
    accentSecondary: "#2dd4bf",
  },
  fonts: {
    mono: "'JetBrains Mono', 'SF Mono', 'Fira Code', monospace",
    display: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
  },
};

interface ThemeContextType {
  theme: Theme;
  toggleTheme: () => void;
  setTheme: (mode: ThemeMode) => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [mode, setMode] = useState<ThemeMode>(() => {
    // Check localStorage first
    const saved = localStorage.getItem("theme");
    if (saved === "light" || saved === "dark") {
      return saved;
    }
    // Check system preference
    if (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) {
      return "dark";
    }
    return "light";
  });

  useEffect(() => {
    // Save to localStorage
    localStorage.setItem("theme", mode);
    // Update body class for global styles
    document.body.className = `theme-${mode}`;
  }, [mode]);

  const toggleTheme = () => {
    setMode((prev) => (prev === "light" ? "dark" : "light"));
  };

  const setTheme = (newMode: ThemeMode) => {
    setMode(newMode);
  };

  const theme = mode === "dark" ? darkTheme : lightTheme;

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (context === undefined) {
    throw new Error("useTheme must be used within a ThemeProvider");
  }
  return context;
}

