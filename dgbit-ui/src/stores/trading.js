import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { tradeApi } from '@/services/api'

export const useTradingStore = defineStore('trading', () => {
  const balance = ref({})
  const positions = ref([])
  const openOrders = ref([])
  const loading = ref(false)
  const error = ref(null)

  const totalBalance = computed(() => {
    if (Array.isArray(balance.value)) {
      return balance.value.reduce((sum, item) => sum + (item.free || 0), 0)
    }
    return Object.values(balance.value).reduce((sum, a) => sum + a, 0)
  })

  const totalPnl = computed(() => positions.value.reduce((sum, p) => sum + (p.unrealized_pnl || 0), 0))

  async function fetchBalance() {
    loading.value = true
    try {
      const response = await tradeApi.getBalance()
      // Backend returns balance as dict like {"USDT": 1000, "BTC": 0.5}
      balance.value = response.data || {}
    } catch (e) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  async function fetchPositions() {
    loading.value = true
    try {
      const response = await tradeApi.getPositions()
      // Backend returns positions as array
      positions.value = response.data || []
    } catch (e) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  async function fetchOpenOrders(symbol = null) {
    loading.value = true
    try {
      const response = await tradeApi.getOpenOrders(symbol)
      // Backend returns orders as array or dict
      openOrders.value = Array.isArray(response.data) ? response.data : []
    } catch (e) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  async function createOrder(orderData) {
    loading.value = true
    try {
      const response = await tradeApi.createOrder(orderData)
      return response.data
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  return { balance, positions, openOrders, loading, error, totalBalance, totalPnl, fetchBalance, fetchPositions, fetchOpenOrders, createOrder }
})
