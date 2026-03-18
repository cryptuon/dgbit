<template>
  <div class="p-6">
    <div class="mb-6">
      <h1 class="text-2xl font-bold">Portfolio</h1>
      <p class="text-gray-400">Your trading accounts and positions</p>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
      <div class="card"><div class="text-gray-400 text-sm">Total Balance</div><div class="text-2xl font-bold mt-1">${{ formatNumber(totalBalance) }}</div></div>
      <div class="card"><div class="text-gray-400 text-sm">Unrealized P&L</div><div class="text-2xl font-bold mt-1" :class="totalPnl >= 0 ? 'text-green-400' : 'text-red-400'">${{ formatNumber(totalPnl) }}</div></div>
      <div class="card"><div class="text-gray-400 text-sm">Open Positions</div><div class="text-2xl font-bold mt-1">{{ positions.length }}</div></div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div class="card">
        <div class="card-header">Asset Balance</div>
        <div v-if="Object.keys(balance).length === 0" class="text-center py-8 text-gray-400">No balance data</div>
        <table v-else class="table">
          <thead><tr><th>Asset</th><th>Available</th></tr></thead>
          <tbody><tr v-for="(amount, asset) in balance" :key="asset"><td class="font-medium">{{ asset }}</td><td>{{ formatNumber(amount, 6) }}</td></tr></tbody>
        </table>
      </div>
      <div class="card">
        <div class="card-header">Open Positions</div>
        <div v-if="positions.length === 0" class="text-center py-8 text-gray-400">No open positions</div>
        <div v-else class="space-y-3">
          <div v-for="pos in positions" :key="pos.symbol" class="p-4 bg-gray-700/50 rounded-lg">
            <div class="flex justify-between">
              <div><span class="font-bold">{{ pos.symbol }}</span><span class="ml-2 px-2 py-0.5 text-xs rounded" :class="pos.side === 'long' ? 'bg-green-400/20 text-green-400' : 'bg-red-400/20 text-red-400'">{{ pos.side?.toUpperCase() }}</span></div>
              <div :class="pos.unrealized_pnl >= 0 ? 'text-green-400' : 'text-red-400'">${{ formatNumber(pos.unrealized_pnl) }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useTradingStore } from '@/stores/trading'

const tradingStore = useTradingStore()
const balance = computed(() => tradingStore.balance)
const positions = computed(() => tradingStore.positions)
const totalBalance = computed(() => tradingStore.totalBalance)
const totalPnl = computed(() => tradingStore.totalPnl)

function formatNumber(num, d=2) {
  if (!num && num !== 0) return '0.00'
  return new Intl.NumberFormat('en-US', { minimumFractionDigits: d, maximumFractionDigits: d }).format(num)
}

onMounted(() => {
  tradingStore.fetchBalance()
  tradingStore.fetchPositions()
})
</script>
