import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'

function formatDate(record) {
  const raw = record.Date || record.Datetime
  if (!raw) return ''
  return new Date(raw).toLocaleDateString()
}

function PriceChart({ ticker, history, loading, error, theme }) {
  if (!ticker) {
    return <p className="text-slate-500 dark:text-slate-400">Select a ticker to see its price history.</p>
  }

  if (loading) {
    return <p className="text-slate-500 dark:text-slate-400">Loading price history for {ticker}...</p>
  }

  if (error) {
    return <p className="text-red-500 dark:text-red-400">Couldn't load price history for {ticker}.</p>
  }

  const data = history.map((record) => ({
    date: formatDate(record),
    close: record.Close,
  }))

  const isDark = theme === 'dark'
  const gridColor = isDark ? '#334155' : '#e2e8f0'
  const tickColor = isDark ? '#94a3b8' : '#64748b'
  const tooltipStyle = isDark
    ? { background: '#1e293b', border: '1px solid #334155', color: '#e2e8f0' }
    : { background: '#ffffff', border: '1px solid #e2e8f0', color: '#1e293b' }

  return (
    <div>
      <h3 className="font-semibold text-slate-900 dark:text-white mb-2">{ticker} — 1 Year Price History</h3>
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
          <XAxis dataKey="date" tick={{ fontSize: 11, fill: tickColor }} minTickGap={40} />
          <YAxis domain={['auto', 'auto']} tick={{ fontSize: 11, fill: tickColor }} />
          <Tooltip contentStyle={tooltipStyle} />
          <Line type="monotone" dataKey="close" stroke="#38bdf8" dot={false} strokeWidth={2} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

export default PriceChart
