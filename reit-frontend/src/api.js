const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

let authToken = null

export function setAuthToken(token) {
  authToken = token
}

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
      ...(options.headers || {}),
    },
  })
  if (!response.ok) {
    throw new Error(`Request to ${path} failed with status ${response.status}`)
  }
  return response.json()
}

function postJson(path, body) {
  return request(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export function getCategories() {
  return request('/categories')
}

export function getEtfs(category) {
  const query = category ? `?category=${encodeURIComponent(category)}` : ''
  return request(`/etfs${query}`)
}

export function getStocks(sector) {
  const query = sector ? `?sector=${encodeURIComponent(sector)}` : ''
  return request(`/stocks${query}`)
}

export function getPriceHistory(ticker) {
  return request(`/price/${encodeURIComponent(ticker)}`)
}

export function askAssistant(question, ticker) {
  return postJson('/assistant', { question, ticker: ticker || undefined })
}

export function getFavourites() {
  return request('/favourites')
}

export function addFavourite(ticker, assetType, name) {
  return postJson('/favourites', { ticker, asset_type: assetType, name })
}

export function removeFavourite(ticker) {
  return request(`/favourites/${encodeURIComponent(ticker)}`, { method: 'DELETE' })
}

export function loginWithGoogle(credential) {
  return postJson('/auth/google', { credential })
}

export function getFinancialInsight(ticker) {
  return postJson(`/insight/${encodeURIComponent(ticker)}`, {})
}

export function getCompanyAnalysis(ticker) {
  return postJson(`/analysis/${encodeURIComponent(ticker)}`, {})
}

export function getWeeklyUpdate(ticker) {
  return postJson(`/weekly-update/${encodeURIComponent(ticker)}`, {})
}
