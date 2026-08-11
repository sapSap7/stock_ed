import { Sun, Moon } from 'lucide-react'

function ThemeToggle({ theme, onToggle }) {
  return (
    <button
      onClick={onToggle}
      className="fixed top-4 right-4 z-50 w-10 h-10 rounded-full bg-white/80 dark:bg-slate-800/80 backdrop-blur flex items-center justify-center hover:bg-slate-100 dark:hover:bg-slate-700 shadow-lg transition-colors text-slate-700 dark:text-slate-200"
      aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
    >
      {theme === 'dark' ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
    </button>
  )
}

export default ThemeToggle
