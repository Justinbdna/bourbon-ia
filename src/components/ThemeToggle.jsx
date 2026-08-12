import { useState, useEffect } from 'react'

const THEME_STORAGE_KEY = 'bourbon_theme_preference'

export default function ThemeToggle() {
  const [isDark, setIsDark] = useState(() => {
    const saved = localStorage.getItem(THEME_STORAGE_KEY)
    if (saved !== null) {
      return saved === 'dark'
    }
    return typeof window !== 'undefined' && window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches
  })

  useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }, [isDark])

  const toggleTheme = () => {
    const nextDark = !isDark
    setIsDark(nextDark)
    localStorage.setItem(THEME_STORAGE_KEY, nextDark ? 'dark' : 'light')
  }

  return (
    <button 
      onClick={toggleTheme}
      className="bg-white dark:bg-neutral-800/50 hover:bg-neutral-100 dark:hover:bg-neutral-700/50 border border-neutral-200 dark:border-neutral-700/50 text-slate-700 dark:text-neutral-300 hover:text-slate-900 dark:hover:text-white px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2 shrink-0"
      title="Bascule entre le thème sombre institutionnel et le thème clair."
    >
      {isDark ? '☀️ Mode Clair' : '🌙 Mode Foncé'}
    </button>
  )
}
