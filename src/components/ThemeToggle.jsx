import { useState, useEffect } from 'react'

export default function ThemeToggle() {
  const [isDark, setIsDark] = useState(false)

  useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }, [isDark])

  return (
    <button 
      onClick={() => setIsDark(!isDark)}
      className="p-2 rounded-md bg-neutre/20 hover:bg-neutre/40 dark:bg-surface dark:hover:bg-surface/80 dark:text-plume text-white font-medium transition-colors shadow-sm text-sm"
    >
      {isDark ? '☀️ Mode Clair' : '🌙 Mode Foncé'}
    </button>
  )
}
