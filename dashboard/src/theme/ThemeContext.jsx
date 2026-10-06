import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

const ThemeContext = createContext(null);
const STORAGE_KEY = "aiops-theme";

function initialTheme() {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === "light" || stored === "dark") return stored;
  } catch {
    /* storage unavailable */
  }
  return "dark";
}

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(initialTheme);
  const [locked, setLocked] = useState(null);

  const effective = locked || theme;

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", effective);
    document.documentElement.style.colorScheme = effective;
  }, [effective]);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch {
      /* storage unavailable */
    }
  }, [theme]);

  const toggle = useCallback(() => {
    setTheme((prev) => (prev === "dark" ? "light" : "dark"));
  }, []);

  const value = useMemo(
    () => ({ theme: effective, preference: theme, toggle, setTheme, lock: setLocked }),
    [effective, theme, toggle]
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used inside ThemeProvider");
  return ctx;
}

export function useForcedTheme(value) {
  const { lock } = useTheme();
  useEffect(() => {
    lock(value);
    return () => lock(null);
  }, [lock, value]);
}
