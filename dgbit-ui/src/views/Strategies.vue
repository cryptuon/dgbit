<template>
  <div class="p-6">
    <div class="flex justify-between items-center mb-6">
      <div>
        <h1 class="text-2xl font-bold">Strategy Manager</h1>
        <p class="text-gray-400">Configure and run trading strategies</p>
      </div>
      <button class="btn btn-primary" @click="showBacktestModal = true">New Backtest</button>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
      <div v-for="strategy in strategies" :key="strategy.name" class="card cursor-pointer hover:border-dgbit-500">
        <div class="flex justify-between">
          <div><h3 class="font-bold text-lg">{{ strategy.name }}</h3><p class="text-sm text-gray-400 mt-1">{{ strategy.description }}</p></div>
          <span class="text-xs text-dgbit-400">v{{ strategy.version }}</span>
        </div>
        <div class="mt-4 flex gap-2">
          <button class="flex-1 btn btn-secondary text-sm py-1" @click="runQuickBacktest(strategy)">Quick Test</button>
          <button class="flex-1 btn btn-primary text-sm py-1">Configure</button>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-header">Recent Backtests</div>
      <div v-if="backtestResults.length === 0" class="text-center py-8 text-gray-400">No backtest results yet</div>
      <table v-else class="table">
        <thead><tr><th>Strategy</th><th>Symbol</th><th>Return</th><th>Win Rate</th><th>Date</th></tr></thead>
        <tbody>
          <tr v-for="r in backtestResults" :key="r.id">
            <td>{{ r.strategy }}</td><td>{{ r.symbol }}</td>
            <td :class="r.total_return >= 0 ? 'text-green-400' : 'text-red-400'">{{ r.total_return >= 0 ? '+' : '' }}{{ r.total_return?.toFixed(2) }}%</td>
            <td>{{ r.win_rate?.toFixed(2) }}%</td>
            <td>{{ formatTime(r.created_at) }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="showBacktestModal" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div class="bg-gray-800 rounded-lg p-6 w-full max-w-md">
        <h2 class="text-xl font-bold mb-4">Run Backtest</h2>
        <div class="space-y-4">
          <div><label class="text-sm text-gray-400">Strategy</label><select v-model="backtestForm.strategy" class="input w-full mt-1"><option v-for="s in strategies" :key="s.name" :value="s.name">{{ s.name }}</option></select></div>
          <div><label class="text-sm text-gray-400">Symbol</label><input v-model="backtestForm.symbol" type="text" class="input w-full mt-1" /></div>
          <div class="grid grid-cols-2 gap-4">
            <div><label class="text-sm text-gray-400">Interval</label><select v-model="backtestForm.interval" class="input w-full mt-1"><option value="1m">1m</option><option value="5m">5m</option><option value="1h">1h</option><option value="4h">4h</option><option value="1d">1d</option></select></div>
            <div><label class="text-sm text-gray-400">Limit</label><input v-model.number="backtestForm.limit" type="number" class="input w-full mt-1" /></div>
          </div>
          <div><label class="text-sm text-gray-400">Initial Capital</label><input v-model.number="backtestForm.initial_capital" type="number" class="input w-full mt-1" /></div>
        </div>
        <div class="flex gap-2 mt-6">
          <button class="flex-1 btn btn-secondary" @click="showBacktestModal = false">Cancel</button>
          <button class="flex-1 btn btn-primary" @click="runBacktest" :disabled="loading">{{ loading ? 'Running...' : 'Run' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useStrategyStore } from '@/stores/strategies'

const strategyStore = useStrategyStore()
const showBacktestModal = ref(false)
const loading = ref(false)
const backtestResults = ref([])

const strategies = ref([
  { name: 'wavelet_reversal', description: 'Wavelet-based mean reversal', version: '1.0.0' },
  { name: 'rsi_divergence', description: 'RSI divergence signals', version: '1.0.0' },
  { name: 'trend_following', description: 'Multi-timeframe trend', version: '1.0.0' },
])

const backtestForm = ref({ strategy: 'wavelet_reversal', symbol: 'BTCUSDT', interval: '1h', limit: 1000, initial_capital: 10000 })

function formatTime(t) { return t ? new Date(t).toLocaleString() : '-' }

async function runQuickBacktest(s) { backtestForm.value.strategy = s.name; showBacktestModal.value = true }

async function runBacktest() {
  loading.value = true
  try {
    const r = await strategyStore.runBacktest(backtestForm.value)
    backtestResults.value.unshift(r)
    showBacktestModal.value = false
  } finally { loading.value = false }
}

onMounted(() => strategyStore.fetchStrategies())
</script>
