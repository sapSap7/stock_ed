import { useState } from 'react'
import { askAssistant } from '../api'

function AssistantChat({ selectedTicker }) {
  const [question, setQuestion] = useState('')
  const [messages, setMessages] = useState([])
  const [sending, setSending] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    const trimmed = question.trim()
    if (!trimmed || sending) return

    setMessages((prev) => [...prev, { role: 'user', text: trimmed }])
    setQuestion('')
    setSending(true)

    try {
      const { answer } = await askAssistant(trimmed, selectedTicker)
      setMessages((prev) => [...prev, { role: 'assistant', text: answer }])
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', text: "Sorry, something went wrong reaching the assistant." },
      ])
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700/50 flex flex-col h-[420px]">
      <div className="px-4 py-3 border-b border-slate-200 dark:border-slate-700/50">
        <h3 className="font-semibold text-slate-900 dark:text-white">Ask the Assistant</h3>
        <p className="text-xs text-slate-500 dark:text-slate-400">
          {selectedTicker
            ? `Questions will include context about ${selectedTicker}.`
            : 'Ask about any stock, ETF, or financial term.'}
        </p>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
        {messages.length === 0 && (
          <p className="text-sm text-slate-400 dark:text-slate-500">
            e.g. "What does expense ratio mean?" or "Explain this ETF"
          </p>
        )}
        {messages.map((m, i) => (
          <div
            key={i}
            className={`text-sm rounded-lg px-3 py-2 max-w-[85%] ${
              m.role === 'user'
                ? 'bg-sky-500 text-white ml-auto'
                : 'bg-slate-100 dark:bg-slate-700 text-slate-800 dark:text-slate-100'
            }`}
          >
            {m.text}
          </div>
        ))}
        {sending && <p className="text-sm text-slate-400 dark:text-slate-500">Thinking...</p>}
      </div>

      <form onSubmit={handleSubmit} className="flex gap-2 p-3 border-t border-slate-200 dark:border-slate-700/50">
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask a question..."
          className="flex-1 px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-100 text-sm placeholder:text-slate-400 dark:placeholder:text-slate-500"
        />
        <button
          type="submit"
          disabled={sending}
          className="px-4 py-2 bg-sky-500 text-white rounded-lg text-sm font-medium hover:bg-sky-600 transition disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </div>
  )
}

export default AssistantChat
