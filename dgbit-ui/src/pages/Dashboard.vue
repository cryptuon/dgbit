<template>
  <section class="w-full">
    <div class="mb-6">
      <p class="text-sm uppercase tracking-wide text-slate-400">System Overview</p>
      <h2 class="text-2xl font-semibold">Welcome back</h2>
      <p class="text-slate-400">Monitor jobs, metrics, and live activity as dgbit evolves into the full platform.</p>
    </div>

    <div class="grid gap-6 md:grid-cols-3">
      <div class="rounded-lg border border-slate-800 bg-slate-900/50 p-5">
        <p class="text-sm text-slate-400">Active Jobs</p>
        <p class="mt-2 text-3xl font-semibold">{{ jobsStore.jobs.length }}</p>
      </div>
      <div class="rounded-lg border border-slate-800 bg-slate-900/50 p-5">
        <p class="text-sm text-slate-400">Environment</p>
        <p class="mt-2 text-3xl font-semibold uppercase">{{ jobsStore.health.environment }}</p>
      </div>
      <div class="rounded-lg border border-slate-800 bg-slate-900/50 p-5">
        <p class="text-sm text-slate-400">API Status</p>
        <p class="mt-2 text-3xl font-semibold">
          <span :class="jobsStore.health.status === 'ok' ? 'text-emerald-400' : 'text-amber-400'">
            {{ jobsStore.health.status }}
          </span>
        </p>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted } from "vue";
import { useJobsStore } from "../stores/jobs";

const jobsStore = useJobsStore();

onMounted(async () => {
  await jobsStore.refreshHealth();
  await jobsStore.fetchJobs();
});
</script>
