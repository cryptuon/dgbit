import { defineStore } from 'pinia'
import { ref } from 'vue'
import wsService from '@/services/websocket'

export const useConnectionStore = defineStore('connection', () => {
  const connected = ref(false)
  const lastHeartbeat = ref(null)

  function connect() {
    wsService.on('connected', () => {
      connected.value = true
      lastHeartbeat.value = new Date()
    })
    wsService.on('disconnected', () => { connected.value = false })
    wsService.connect()
  }

  function disconnect() {
    wsService.disconnect()
    connected.value = false
  }

  return { connected, lastHeartbeat, connect, disconnect }
})
