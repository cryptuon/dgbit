import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { marketApi } from '@/services/api'

export const useMarketStore = defineStore('market', () => {
  const symbols = ref([])
  const tickers = ref([])
  const selectedSymbol = ref('BTCUSDT')
  const klines = ref([])
  const loading = ref(false)
  const error = ref(null)

  const btcPrice = computed(() => {
    const btc = tickers.value.find(t => t.symbol === 'BTCUSDT')
    return btc?.price || 0
  })

  const ethPrice = computed(() => {
    const eth = tickers.value.find(t => t.symbol === 'ETHUSDT')
    return eth?.price || 0
  })

  async function fetchSymbols() {
    try {
      const response = await marketApi.getSymbols()
      symbols.value = response.data
    } catch (e) {
      error.value = e.message
    }
  }

  async function fetchTickers(symbol = null) {
    loading.value = true
    try {
      const response = await marketApi.getTickers(symbol)
      tickers.value = response.data
    } catch (e) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  async function fetchKlines(symbol, interval = '1h', limit = 100) {
    loading.value = true
    try {
      const response = await marketApi.getKlines(symbol, interval, limit)
      klines.value = response.data
    } catch (e) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  function setSelectedSymbol(symbol) {
    selectedSymbol.value = symbol
  }

  return { symbols, tickers, selectedSymbol, klines, loading, error, btcPrice, ethPrice, fetchSymbols, fetchTickers, fetchKlines, setSelectedSymbol }
})
