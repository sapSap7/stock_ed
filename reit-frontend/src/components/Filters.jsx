import { Search } from 'lucide-react'

function Filters({
  assetType,
  onAssetTypeChange,
  categories,
  selectedCategory,
  onCategoryChange,
  searchQuery,
  onSearchChange,
}) {
  return (
    <div className="flex flex-wrap items-center gap-4 mb-6">
      <div className="flex rounded-lg border border-slate-300 dark:border-slate-700 overflow-hidden">
        {['etfs', 'stocks'].map((type) => (
          <button
            key={type}
            onClick={() => onAssetTypeChange(type)}
            className={`px-4 py-2 text-sm font-medium capitalize transition ${
              assetType === type
                ? 'bg-sky-500 text-white'
                : 'bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700'
            }`}
          >
            {type}
          </button>
        ))}
      </div>

      <select
        value={selectedCategory}
        onChange={(e) => onCategoryChange(e.target.value)}
        className="px-4 py-2 rounded-lg border border-slate-300 dark:border-slate-700 text-sm text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-800"
      >
        <option value="">
          {assetType === 'etfs' ? 'All categories' : 'All sectors'}
        </option>
        {categories.map((c) => (
          <option key={c} value={c}>
            {c}
          </option>
        ))}
      </select>

      <div className="relative flex-1 min-w-[200px]">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Search by ticker or name..."
          className="w-full pl-9 pr-4 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 text-sm placeholder:text-slate-400 dark:placeholder:text-slate-500"
        />
      </div>
    </div>
  )
}

export default Filters
