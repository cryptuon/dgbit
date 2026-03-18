<template>
  <div class="p-6">
    <div class="mb-6">
      <h1 class="text-2xl font-bold">Dashboard</h1>
      <p class="text-gray-400">Overview of your trading platform</p>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      <div class="card">
        <div class="text-gray-400 text-sm">BTC/USDT</div>
        <div class="text-2xl font-bold mt-1">${{ formatNumber(marketStore.btcPrice) }}</div>
        <div class="text-sm text-green-400">+2.50%</div>
      </div>
      <div class="card">
        <div class="text-gray-400 text-sm">ETH/USDT</div>
        <div class="text-2xl font-bold mt-1">${{ formatNumber(marketStore.ethPrice) }}</div>
        <div class="text-sm text-green-400">+1.80%</div>
      </div>
      <div class="card">
        <div class="text-gray-400 text-sm">Portfolio Value</div>
        <div class="text-2xl font-bold mt-1">${{ formatNumber(tradingStore.totalBalance) }}</div>
      </div>
      <div class="card">
        <div class="text-gray-400 text-sm">Unrealized P&L</div>
        <div class="text-2xl font-bold mt-1" :class="tradingStore.totalPnl >= 0 ? 'text-green-400' : 'text-red-400'">
          ${{ formatNumber(tradingStore.totalPnl) }}
        </div>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div class="lg:col-span-2 card">
        <div class="card-header">Open Positions</div>
        <div v-if="tradingStore.positions.length === 0" class="text-center py-8 text-gray-400">No open positions</div>
        <table v-else class="table">
          <thead><tr><th>Symbol</th><th>Side</th><th>Size</th><th>Entry</th><th>P&L</th></tr></thead>
          <tbody>
            <tr v-for="pos in tradingStore.positions" :key="pos.symbol">
              <td>{{ pos.symbol }}</td>
              <td :class="pos.side === 'long' ? 'text-green-400' : 'text-red-400'">{{ pos.side?.toUpperCase() }}</td>
              <td>{{ formatNumber(pos.quantity) }}</td>
              <td>${{ formatNumber(pos.entry_price) }}</td>
              <td :class="pos.unrealized_pnl >= 0 ? 'text-green-400' : 'text-red-400'">${{ formatNumber(pos.unrealized_pnl) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="card">
        <div class="card-header">Open Orders</div>
        <div v-if="tradingStore.openOrders.length === 0" class="text-center py-8 text-gray-400">No open orders</div>
        <div v-else class="space-y-2">
          <div v-for="order in tradingStore.openOrders.slice(0, 5)" :key="order.order_id" class="p-3 bg-gray-700/50 rounded-lg">
            <div class="flex justify-between">
              <span :class="order.side === 'buy' ? 'text-green-400' : 'text-red-400'">{{ order.side?.toUpperCase() }}</span>
              <span class="text-sm text-gray-400">{{ order.order_type }}</span>
            </div>
            <div class="text-sm mt-1">{{ order.symbol }} x {{ order.quantity }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useMarketStore } from '@/stores/market'
import { useTradingStore } from '@/stores/trading'

const marketStore = useMarketStore()
const tradingStore = useTradingStore()

function formatNumber(num, d=2) {
  if (!num) return '0.00'
  return new Intl.NumberFormat('en-US', { minimumFractionDigits: d, maximumFractionDigits: d }).format(num)
}

onMounted(() => {
  marketStore.fetchSymbols()
  tradingStore.fetchPositions()
  tradingStore.fetchOpenOrders()
})
</script>
