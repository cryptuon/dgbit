import { defineStore } from 'pinia'
import { ref } from 'vue'
import { systemApi, jobApi } from '@/services/api'

export const useSystemStore = defineStore('system', () => {
  const services = ref([])
  const jobs = ref([])
  const health = ref(null)
  const loading = ref(false)
  const error = ref(null)

  async function fetchServices() {
    loading.value = true
    try {
      const response = await systemApi.getServices()
      services.value = response.data
    } catch (e) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  async function fetchHealth() {
    try {
      const response = await systemApi.getHealth()
      health.value = response.data
    } catch (e) {
      error.value = e.message
    }
  }

  async function fetchJobs(status = null, limit = 50) {
    loading.value = true
    try {
      const response = await jobApi.listJobs(status, limit)
      jobs.value = response.data
    } catch (e) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  return { services, jobs, health, loading, error, fetchServices, fetchHealth, fetchJobs }
})
