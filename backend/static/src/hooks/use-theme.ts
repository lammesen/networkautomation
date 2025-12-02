import { useEffect, useState, useCallback } from "react";

export type Theme = "light" | "dark" | "system";

const THEME_KEY = "theme";

function getSystemTheme(): "light" | "dark" {
  if (typeof window === "undefined") return "light";
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

function getStoredTheme(): Theme {
  if (typeof window === "undefined") return "system";
  const stored = localStorage.getItem(THEME_KEY);
  // Handle admin panel's "auto" value as "system"
  if (stored === "auto") return "system";
  if (stored === "light" || stored === "dark" || stored === "system") {
    return stored;
  }
  return "system";
}

function applyTheme(theme: Theme) {
  const root = document.documentElement;
  const effectiveTheme = theme === "system" ? getSystemTheme() : theme;

  if (effectiveTheme === "dark") {
    root.classList.add("dark");
  } else {
    root.classList.remove("dark");
  }

  // Also set data-theme for admin panel compatibility
  root.dataset.theme = theme === "system" ? "auto" : theme;
}

export function useTheme() {
  const [theme, setThemeState] = useState<Theme>(() => getStoredTheme());
  const [resolvedTheme, setResolvedTheme] = useState<"light" | "dark">(() =>
    theme === "system" ? getSystemTheme() : theme
  );

  const setTheme = useCallback((newTheme: Theme) => {
    setThemeState(newTheme);
    // Store using admin-compatible values
    localStorage.setItem(THEME_KEY, newTheme === "system" ? "auto" : newTheme);
    applyTheme(newTheme);

    // Dispatch storage event for cross-tab sync
    window.dispatchEvent(
      new StorageEvent("storage", {
        key: THEME_KEY,
        newValue: newTheme === "system" ? "auto" : newTheme,
      })
    );
  }, []);

  // Update resolved theme when system preference changes
  useEffect(() => {
    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");

    const handleChange = () => {
      if (theme === "system") {
        const newResolved = getSystemTheme();
        setResolvedTheme(newResolved);
        applyTheme("system");
      }
    };

    mediaQuery.addEventListener("change", handleChange);
    return () => mediaQuery.removeEventListener("change", handleChange);
  }, [theme]);

  // Apply theme on mount and when theme changes
  useEffect(() => {
    applyTheme(theme);
    setResolvedTheme(theme === "system" ? getSystemTheme() : theme);
  }, [theme]);

  // Sync with localStorage changes from other tabs/windows (including admin)
  useEffect(() => {
    const handleStorage = (e: StorageEvent) => {
      if (e.key === THEME_KEY) {
        const newValue = e.newValue;
        let newTheme: Theme = "system";
        if (newValue === "auto") newTheme = "system";
        else if (newValue === "light" || newValue === "dark") newTheme = newValue;
        
        setThemeState(newTheme);
        applyTheme(newTheme);
        setResolvedTheme(newTheme === "system" ? getSystemTheme() : newTheme);
      }
    };

    window.addEventListener("storage", handleStorage);
    return () => window.removeEventListener("storage", handleStorage);
  }, []);

  return {
    theme,
    setTheme,
    resolvedTheme,
  };
}

// Immediate theme application for SSR/hydration (prevents FOUC)
// This should be called in a script tag before body renders
export function initTheme() {
  const theme = getStoredTheme();
  applyTheme(theme);
}
