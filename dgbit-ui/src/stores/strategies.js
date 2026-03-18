import { defineStore } from 'pinia'
import { ref } from 'vue'
import { strategyApi } from '@/services/api'

export const useStrategyStore = defineStore('strategies', () => {
  const strategies = ref([])
  const activeStrategy = ref(null)
  const backtestResults = ref(null)
  const loading = ref(false)
  const error = ref(null)

  async function fetchStrategies() {
    loading.value = true
    try {
      const response = await strategyApi.listStrategies()
      strategies.value = response.data
    } catch (e) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  async function runBacktest(config) {
    loading.value = true
    try {
      const response = await strategyApi.runBacktest(config)
      backtestResults.value = response.data
      return response.data
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  return { strategies, activeStrategy, backtestResults, loading, error, fetchStrategies, runBacktest }
})
