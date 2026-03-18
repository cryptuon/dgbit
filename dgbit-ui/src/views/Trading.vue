<template>
  <div class="p-6">
    <div class="flex justify-between items-center mb-6">
      <div>
        <h1 class="text-2xl font-bold">Charts & Trading</h1>
        <p class="text-gray-400">Real-time market data and trading</p>
      </div>
      <div class="flex gap-2">
        <select v-model="selectedSymbol" class="input">
          <option v-for="sym in popularSymbols" :key="sym" :value="sym">{{ sym }}</option>
        </select>
        <select v-model="interval" class="input">
          <option value="1m">1m</option>
          <option value="5m">5m</option>
          <option value="15m">15m</option>
          <option value="1h">1h</option>
          <option value="4h">4h</option>
          <option value="1d">1d</option>
        </select>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-4 gap-6">
      <div class="lg:col-span-3 card">
        <div class="card-header flex justify-between items-center">
          <span>{{ selectedSymbol }} / USDT</span>
          <span v-if="currentPrice" class="text-2xl font-bold text-dgbit-400">${{ formatNumber(currentPrice) }}</span>
        </div>
        <div class="h-96 bg-gray-900 rounded-lg flex items-center justify-center">
          <div class="text-center">
            <p class="text-gray-400">Chart Component</p>
            <p class="text-sm text-gray-500 mt-2">{{ selectedSymbol }} - {{ interval }} timeframe</p>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">Place Order</div>
        <div class="flex gap-2 mb-4">
          <button class="flex-1 py-2 rounded-lg font-medium" :class="orderForm.side === 'buy' ? 'bg-green-600 text-white' : 'bg-gray-700'" @click="orderForm.side = 'buy'">Buy</button>
          <button class="flex-1 py-2 rounded-lg font-medium" :class="orderForm.side === 'sell' ? 'bg-red-600 text-white' : 'bg-gray-700'" @click="orderForm.side = 'sell'">Sell</button>
        </div>
        <div class="flex gap-2 mb-4">
          <button v-for="type in ['market', 'limit', 'stop']" :key="type" class="flex-1 py-1.5 text-sm rounded-lg capitalize" :class="orderForm.type === type ? 'bg-dgbit-600 text-white' : 'bg-gray-700'" @click="orderForm.type = type">{{ type }}</button>
        </div>
        <div class="mb-4">
          <label class="text-sm text-gray-400">Price (USDT)</label>
          <input v-model.number="orderForm.price" type="number" step="0.01" class="input w-full mt-1" :disabled="orderForm.type === 'market'" />
        </div>
        <div class="mb-4">
          <label class="text-sm text-gray-400">Quantity</label>
          <input v-model.number="orderForm.quantity" type="number" step="0.001" class="input w-full mt-1" />
        </div>
        <div class="mb-4 p-3 bg-gray-700/50 rounded-lg">
          <div class="text-sm text-gray-400">Total</div>
          <div class="text-lg font-bold">${{ formatNumber(orderTotal) }}</div>
        </div>
        <button class="w-full py-3 rounded-lg font-bold" :class="orderForm.side === 'buy' ? 'bg-green-600 hover:bg-green-700' : 'bg-red-600 hover:bg-red-700'" @click="submitOrder" :disabled="loading">
          {{ loading ? 'Processing...' : (orderForm.side.toUpperCase() + ' ' + selectedSymbol) }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useMarketStore } from '@/stores/market'
import { useTradingStore } from '@/stores/trading'

const marketStore = useMarketStore()
const tradingStore = useTradingStore()
const selectedSymbol = ref('BTCUSDT')
const interval = ref('1h')
const currentPrice = ref(0)
const loading = ref(false)
const popularSymbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'ADAUSDT', 'DOGEUSDT']

const orderForm = ref({ side: 'buy', type: 'market', price: 0, quantity: 0.001, exchange: 'bybit' })
const orderTotal = computed(() => (orderForm.value.type === 'market' ? currentPrice.value : orderForm.value.price) * orderForm.value.quantity)

function formatNumber(num, d=2) {
  if (!num) return '0.00'
  return new Intl.NumberFormat('en-US', { minimumFractionDigits: d, maximumFractionDigits: d }).format(num)
}

async function submitOrder() {
  loading.value = true
  try {
    await tradingStore.createOrder({ symbol: selectedSymbol.value, ...orderForm.value })
    orderForm.value.quantity = 0.001
  } finally { loading.value = false }
}

async function fetchData() {
  await marketStore.fetchKlines(selectedSymbol.value, interval.value)
  if (marketStore.klines.data?.length) currentPrice.value = marketStore.klines.data[marketStore.klines.data.length - 1].close
}

watch([selectedSymbol, interval], fetchData)
onMounted(fetchData)
</script>
