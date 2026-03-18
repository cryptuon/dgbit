<template>
  <div class="p-6">
    <div class="mb-6">
      <h1 class="text-2xl font-bold">System Monitor</h1>
      <p class="text-gray-400">Service status and job management</p>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-6">
      <div v-for="service in services" :key="service.name" class="card">
        <div class="flex justify-between items-start">
          <div><div class="font-medium">{{ service.name }}</div><div class="text-xs text-gray-400 mt-1">{{ service.description }}</div></div>
          <span class="w-3 h-3 rounded-full" :class="service.status === 'running' ? 'bg-green-400' : service.status === 'stopped' ? 'bg-red-400' : 'bg-yellow-400'"></span>
        </div>
        <div class="mt-3 flex gap-2">
          <button v-if="service.status !== 'running'" class="flex-1 btn btn-success text-xs py-1" @click="service.status = 'running'">Start</button>
          <button v-if="service.status === 'running'" class="flex-1 btn btn-danger text-xs py-1" @click="service.status = 'stopped'">Stop</button>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div class="card">
        <div class="card-header flex justify-between">
          <span>Job Queue</span>
          <select v-model="jobFilter" class="input text-sm"><option value="">All</option><option value="pending">Pending</option><option value="running">Running</option><option value="completed">Completed</option></select>
        </div>
        <div v-if="filteredJobs.length === 0" class="text-center py-8 text-gray-400">No jobs found</div>
        <div v-else class="space-y-2">
          <div v-for="job in filteredJobs.slice(0, 5)" :key="job.uuid" class="p-3 bg-gray-700/50 rounded-lg">
            <div class="flex justify-between">
              <div class="font-medium text-sm">{{ job.job_type }}</div>
              <span class="px-2 py-0.5 text-xs rounded" :class="{ 'bg-yellow-400/20 text-yellow-400': job.status === 'pending', 'bg-blue-400/20 text-blue-400': job.status === 'running', 'bg-green-400/20 text-green-400': job.status === 'completed' }">{{ job.status }}</span>
            </div>
            <div class="text-xs text-gray-400 mt-1">{{ job.uuid?.slice(0, 8) }}...</div>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">System Health</div>
        <div class="space-y-3">
          <div class="flex justify-between p-3 bg-gray-700/50 rounded-lg">
            <div class="flex items-center gap-3"><div class="w-10 h-10 bg-dgbit-600/20 rounded-lg flex items-center justify-center"><svg class="w-6 h-6 text-dgbit-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" /></svg></div><div><div class="font-medium">API Server</div><div class="text-xs text-gray-400">FastAPI backend</div></div></div>
            <span :class="health.api ? 'text-green-400' : 'text-red-400'">{{ health.api ? 'Online' : 'Offline' }}</span>
          </div>
          <div class="flex justify-between p-3 bg-gray-700/50 rounded-lg">
            <div class="flex items-center gap-3"><div class="w-10 h-10 bg-purple-600/20 rounded-lg flex items-center justify-center"><svg class="w-6 h-6 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4" /></svg></div><div><div class="font-medium">Database</div><div class="text-xs text-gray-400">SQLite</div></div></div>
            <span :class="health.database ? 'text-green-400' : 'text-red-400'">{{ health.database ? 'Connected' : 'Disconnected' }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useSystemStore } from '@/stores/system'

const systemStore = useSystemStore()
const jobFilter = ref('')

const services = ref([
  { name: 'API', description: 'FastAPI Server', status: 'running' },
  { name: 'Event Bus', description: 'NNG PUB/SUB', status: 'running' },
  { name: 'Data Service', description: 'Market Data', status: 'running' },
  { name: 'Job Queue', description: 'Background Jobs', status: 'running' },
  { name: 'Strategy', description: 'Strategy Engine', status: 'stopped' },
])

const health = ref({ api: true, database: true })
const jobs = ref([
  { uuid: 'abc12345', job_type: 'backtest', status: 'completed' },
  { uuid: 'def67890', job_type: 'data_fetch', status: 'running' },
])

const filteredJobs = computed(() => jobFilter.value ? jobs.value.filter(j => j.status === jobFilter.value) : jobs.value)

onMounted(() => { systemStore.fetchHealth() })
</script>
