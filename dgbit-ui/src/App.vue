<template>
  <div class="min-h-screen flex flex-col">
    <header class="border-b border-slate-800 bg-slate-900">
      <div class="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <h1 class="text-xl font-semibold tracking-tight">dgbit Control Center</h1>
        <nav class="space-x-4 text-sm">
          <RouterLink class="hover:text-white text-slate-300" to="/">Dashboard</RouterLink>
          <RouterLink class="hover:text-white text-slate-300" to="/backtests">Backtests</RouterLink>
        </nav>
      </div>
    </header>
    <main class="mx-auto flex w-full max-w-6xl flex-1 px-6 py-8">
      <RouterView />
    </main>
  </div>
</template>

<script setup lang="ts">
import { RouterLink, RouterView } from "vue-router";
</script>
