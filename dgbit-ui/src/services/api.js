import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request interceptor
api.interceptors.request.use(
  (config) => {
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message)
    return Promise.reject(error)
  }
)

export default api

// Market Data API (uses /api/data/* endpoints)
export const marketApi = {
  getKlines: (symbol, interval = '1h', limit = 100) =>
    api.get('/data/klines', { params: { symbol, interval, limit } }),
  getTickers: (symbol = null) =>
    api.get('/data/klines', { params: { symbol, interval: '1h', limit: 1 } }),
  getSymbols: () => api.get('/data/symbols')
}

// Trading API (uses /api/execution/* endpoints)
export const tradeApi = {
  getBalance: () =>
    api.get('/execution/balance'),
  getPositions: () =>
    api.get('/execution/positions'),
  createOrder: (orderData) => api.post('/execution/orders', orderData),
  cancelOrder: (orderId, symbol) =>
    api.delete(`/execution/orders/${orderId}`, { params: { symbol } }),
  getOpenOrders: (symbol = null) =>
    api.get('/execution/orders', { params: { symbol } })
}

// Strategy API (uses /api/strategies endpoint)
export const strategyApi = {
  listStrategies: () => api.get('/strategies'),
  getStrategy: (name) => api.get(`/strategies/${name}`),
  runBacktest: (config) => api.post('/backtests', config),
  getBacktestResults: (id) => api.get(`/backtests/${id}`)
}

// Job API (uses /api/jobs endpoints)
export const jobApi = {
  listJobs: (status = null, limit = 50) =>
    api.get('/jobs', { params: { status, limit } }),
  getJob: (jobId) => api.get(`/jobs/${jobId}`)
}

// System API (uses /api/health endpoint)
export const systemApi = {
  getHealth: () => api.get('/health'),
  getServices: () => api.get('/health')
}
