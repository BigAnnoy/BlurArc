import { useState, useEffect } from 'react';

type Theme = 'light' | 'dark' | 'system';

// 从后端加载主题设置
async function loadThemeFromBackend(): Promise<Theme | null> {
  try {
    const res = await fetch('/api/settings/theme');
    if (res.ok) {
      const data = await res.json();
      return data.theme as Theme;
    }
  } catch (error) {
    console.error('Failed to load theme from backend:', error);
  }
  return null;
}

// 保存主题到后端配置
async function saveThemeToBackend(theme: Theme) {
  try {
    await fetch('/api/settings/theme', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ theme }),
    });
  } catch (error) {
    console.error('Failed to save theme to backend:', error);
  }
}

export function useTheme() {
  const [theme, setTheme] = useState<Theme>(() => {
    const stored = localStorage.getItem('theme');
    return (stored as Theme) || 'system';
  });
  const [initialized, setInitialized] = useState(false);

  // 初始化时从后端加载主题（优先级：后端 > localStorage 默认值）
  useEffect(() => {
    if (initialized) return;

    loadThemeFromBackend().then((backendTheme) => {
      if (backendTheme) {
        localStorage.setItem('theme', backendTheme);
        setTheme(backendTheme);
      }
      setInitialized(true);
    });
  }, [initialized]);

  // 应用主题并同步到后端
  useEffect(() => {
    if (!initialized) return;

    const applyTheme = () => {
      const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      const isDark = theme === 'dark' || (theme === 'system' && systemPrefersDark);
      document.documentElement.classList.toggle('dark', isDark);
    };

    applyTheme();

    // 保存到 localStorage（立即生效）
    localStorage.setItem('theme', theme);

    // 同步到后端配置（异步，不阻塞）
    saveThemeToBackend(theme);

    // Listen for system theme changes
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handler = () => {
      if (theme === 'system') {
        applyTheme();
      }
    };
    mediaQuery.addEventListener('change', handler);
    return () => mediaQuery.removeEventListener('change', handler);
  }, [theme, initialized]);

  const toggleTheme = () => {
    setTheme((prev) => {
      if (prev === 'light') return 'dark';
      if (prev === 'dark') return 'system';
      return 'light';
    });
  };

  return { theme, setTheme, toggleTheme };
}
