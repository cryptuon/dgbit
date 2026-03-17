<template>
  <section class="flex w-full flex-col gap-6">
    <div>
      <h2 class="text-2xl font-semibold">Backtests</h2>
      <p class="text-slate-400">Trigger runs through dgbit-api and observe progress in real time.</p>
    </div>

    <form class="grid gap-4 rounded-lg border border-slate-800 bg-slate-900/50 p-5" @submit.prevent="submit">
      <div class="grid gap-2 sm:grid-cols-2">
        <label class="text-sm text-slate-400">
          Symbol
          <input v-model="symbol" type="text" class="mt-1 w-full rounded-md border border-slate-700 bg-slate-950 p-2" />
        </label>
        <label class="text-sm text-slate-400">
          Limit
          <input v-model.number="limit" type="number" class="mt-1 w-full rounded-md border border-slate-700 bg-slate-950 p-2" />
        </label>
      </div>
      <button
        type="submit"
        class="inline-flex w-full items-center justify-center rounded-md bg-emerald-500 px-4 py-2 font-semibold text-slate-900 transition hover:bg-emerald-400 sm:w-auto"
      >
        Schedule Backtest
      </button>
    </form>

    <section>
      <h3 class="mb-3 text-lg font-semibold">Recent Jobs</h3>
      <div class="grid gap-4">
        <JobCard v-for="job in jobsStore.jobs" :key="job.id" :job="job" />
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useJobsStore } from "../stores/jobs";
import JobCard from "../components/JobCard.vue";

const jobsStore = useJobsStore();
const symbol = ref("BTCUSDT");
const limit = ref(500);

onMounted(async () => {
  await jobsStore.fetchJobs();
});

const submit = async () => {
  await jobsStore.scheduleBacktest({
    symbol: symbol.value,
    limit: limit.value,
  });
};
</script>
