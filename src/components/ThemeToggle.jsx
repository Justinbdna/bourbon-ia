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
      className="bg-neutral-800/50 hover:bg-neutral-700/50 border border-neutral-700/50 text-neutral-300 hover:text-white px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2 shrink-0"
    >
      {isDark ? '☀️ Mode Clair' : '🌙 Mode Foncé'}
    </button>
  )
}
