<template>
  <div class="min-h-screen flex">
    <!-- Sidebar -->
    <aside class="w-64 bg-gray-800 border-r border-gray-700 flex flex-col">
      <!-- Logo -->
      <div class="p-4 border-b border-gray-700">
        <h1 class="text-xl font-bold text-dgbit-400">DGBIT</h1>
        <p class="text-xs text-gray-400">Trading Platform</p>
      </div>

      <!-- Navigation -->
      <nav class="flex-1 p-4 space-y-1">
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="nav-link"
          :class="{ 'nav-link-active': $route.path === item.path }"
        >
          <component :is="item.icon" class="w-5 h-5 mr-3" />
          {{ item.name }}
        </router-link>
      </nav>

      <!-- Service Status -->
      <div class="p-4 border-t border-gray-700">
        <div class="text-xs text-gray-400 mb-2">Service Status</div>
        <div class="flex items-center gap-2">
          <span
            class="w-2 h-2 rounded-full"
            :class="apiConnected ? 'bg-green-400' : 'bg-red-400'"
          ></span>
          <span class="text-sm">{{ apiConnected ? 'Connected' : 'Disconnected' }}</span>
        </div>
      </div>
    </aside>

    <!-- Main Content -->
    <main class="flex-1 overflow-auto">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  ChartBarIcon,
  CurrencyDollarIcon,
  SignalIcon,
  CpuChipIcon,
  HomeIcon,
} from '@heroicons/vue/24/outline'
import { useConnectionStore } from '@/stores/connection'

const router = useRouter()
const connectionStore = useConnectionStore()
const apiConnected = ref(false)

const navItems = [
  { name: 'Dashboard', path: '/', icon: HomeIcon },
  { name: 'Charts & Trading', path: '/trading', icon: ChartBarIcon },
  { name: 'Portfolio', path: '/portfolio', icon: CurrencyDollarIcon },
  { name: 'Strategies', path: '/strategies', icon: SignalIcon },
  { name: 'System', path: '/system', icon: CpuChipIcon },
]

onMounted(() => {
  connectionStore.connect()
  apiConnected.value = connectionStore.connected
})

onUnmounted(() => {
  connectionStore.disconnect()
})
</script>

<style scoped>
.nav-link {
  @apply flex items-center px-4 py-3 text-gray-300 hover:bg-gray-700 rounded-lg transition-colors duration-200;
}

.nav-link-active {
  @apply bg-dgbit-600/20 text-dgbit-400 border-l-2 border-dgbit-400;
}
</style>
