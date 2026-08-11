import { Heart } from 'lucide-react'

function TickerList({ items, assetType, selectedTicker, onSelect, loading, isFavourite, onToggleFavourite }) {
  if (loading) {
    return <p className="text-slate-500 dark:text-slate-400">Loading...</p>
  }

  if (items.length === 0) {
    return <p className="text-slate-500 dark:text-slate-400">No results for this filter.</p>
  }

  return (
    <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {items.map((item) => {
        const favourited = isFavourite(item.ticker)
        return (
          <div
            key={item.ticker}
            className={`relative text-left rounded-xl p-4 transition border ${
              selectedTicker === item.ticker
                ? 'bg-white dark:bg-slate-800 border-sky-500 ring-1 ring-sky-500'
                : 'bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700/50 hover:border-slate-300 dark:hover:border-slate-600'
            }`}
          >
            <button
              onClick={() => onToggleFavourite(item)}
              className="absolute top-3 right-3 text-slate-400 dark:text-slate-500 hover:text-pink-400 transition-colors"
              aria-label={favourited ? `Remove ${item.ticker} from favourites` : `Add ${item.ticker} to favourites`}
            >
              <Heart className="w-4 h-4" fill={favourited ? 'currentColor' : 'none'} color={favourited ? '#f472b6' : 'currentColor'} />
            </button>

            <button onClick={() => onSelect(item.ticker)} className="text-left w-full pr-6">
              <p className="font-semibold text-slate-900 dark:text-white">{item.ticker}</p>
              <p className="text-sm text-slate-500 dark:text-slate-400 truncate">{item.name}</p>
              <p className="text-xs text-slate-400 dark:text-slate-500 mt-2">
                {assetType === 'etfs' ? item.category : item.sector}
              </p>
            </button>
          </div>
        )
      })}
    </div>
  )
}

export default TickerList
