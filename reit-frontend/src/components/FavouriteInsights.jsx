import { useState } from 'react'
import { TrendingUp, Newspaper, Building2 } from 'lucide-react'
import { getFinancialInsight, getCompanyAnalysis, getWeeklyUpdate } from '../api'

const INSIGHT_TYPES = [
  { key: 'insight', label: 'Financial Insight', icon: TrendingUp, fetcher: getFinancialInsight, field: 'insight' },
  { key: 'update', label: 'Weekly Update', icon: Newspaper, fetcher: getWeeklyUpdate, field: 'update' },
  { key: 'analysis', label: 'Company Analysis', icon: Building2, fetcher: getCompanyAnalysis, field: 'analysis' },
]

function FavouriteInsights({ ticker }) {
  const [active, setActive] = useState(null)
  const [results, setResults] = useState({})
  const [loading, setLoading] = useState(null)
  const [errors, setErrors] = useState({})

  async function handleFetch(type) {
    setActive(type.key)
    if (results[type.key] || loading === type.key) return

    setLoading(type.key)
    setErrors((prev) => ({ ...prev, [type.key]: null }))
    try {
      const data = await type.fetcher(ticker)
      setResults((prev) => ({ ...prev, [type.key]: data[type.field] }))
    } catch {
      setErrors((prev) => ({ ...prev, [type.key]: 'Something went wrong fetching this.' }))
    } finally {
      setLoading(null)
    }
  }

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700/50 p-4 mt-4">
      <h3 className="font-semibold text-slate-900 dark:text-white mb-3">AI Insights for {ticker}</h3>

      <div className="flex flex-wrap gap-2 mb-4">
        {INSIGHT_TYPES.map((type) => (
          <button
            key={type.key}
            onClick={() => handleFetch(type)}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition ${
              active === type.key
                ? 'bg-sky-500 text-white'
                : 'bg-slate-100 dark:bg-slate-900 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'
            }`}
          >
            <type.icon className="w-4 h-4" />
            {type.label}
          </button>
        ))}
      </div>

      {active && (
        <div className="text-sm text-slate-700 dark:text-slate-200 leading-relaxed whitespace-pre-wrap">
          {loading === active && <p className="text-slate-400">Generating...</p>}
          {errors[active] && <p className="text-red-500 dark:text-red-400">{errors[active]}</p>}
          {!loading && results[active] && results[active]}
        </div>
      )}
    </div>
  )
}

export default FavouriteInsights
